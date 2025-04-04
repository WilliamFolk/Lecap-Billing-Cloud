import requests
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.shortcuts import render, redirect
from django.conf import settings
from accounts.models import AdminSettings
from .models import  ProjectRate, DefaultRoleRate
from accounts.forms import AdminSettingsForm, CustomUserForm
from LecapProject.kaiten_api import fetch_kaiten_roles, fetch_kaiten_projects, fetch_kaiten_cards, fetch_kaiten_time_logs
from django.forms import modelformset_factory, ModelForm, HiddenInput
from datetime import datetime
import pytz
from django.http import HttpResponse
from docx import Document
from docxTemplate.models import TemplateFile
from docxTemplate.views import insert_table_after, set_table_borders, insert_paragraph_after_table, convert_number_to_text
from django.forms import ModelForm, HiddenInput
from .models import ProjectRate
from .forms import DefaultRoleRateFormSet
from docx.shared import Inches

User = get_user_model()

@login_required
def templates_view(request):
    return render(request, 'templates.html')

@login_required
def administration_view(request):
    # Если пользователь — суперпользователь, можно сразу редиректить в панель администратора
    """if request.user.is_superuser:
        return redirect('admin:index')"""
    # Иначе можно отобразить кастомную страницу редактирования пользователей
    return render(request, 'custom_admin_users.html')

@login_required
def rates_view(request):
    admin_settings, _ = AdminSettings.objects.get_or_create(pk=1)
    domain = admin_settings.url_domain_value_id
    bearer_key = admin_settings.api_auth_key

    # Получение список проектов из API (сохранение в сессии, чтобы не запрашивать повторно), может сильно снизить 
    # нагрузку на Kaiten, но тогда не прогрузятся новые проекты
    """ projects = request.session.get('projects')
    if not projects:
        projects = fetch_kaiten_projects(domain, bearer_key)
        request.session['projects'] = projects
        valid_project_ids = [str(project['id']) for project in projects]
        # Удаляет все ProjectRate, которые относятся к несуществующим проектам
        ProjectRate.objects.exclude(project_id__in=valid_project_ids).delete() """
    projects = fetch_kaiten_projects(domain, bearer_key)

    # Определяет выбранный проект: если GET-параметры не заданы, выбирает первый проект
    project_id = request.GET.get('project_id')
    project_title = request.GET.get('project_title', '')
    if project_id and not project_title:
        for project in projects:
            if str(project['id']) == str(project_id):
                project_title = project['title']
                break
    if not project_id and projects:
        project_id = str(projects[0]['id'])
        project_title = projects[0]['title']

    # Определяет formset для редактирования ставок (только поле rate)
    ProjectRateFormSet = modelformset_factory(ProjectRate, form=ProjectRateForm, extra=0)
    rates_formset = None

    if project_id:
        roles = fetch_kaiten_roles(domain, bearer_key)
        current_role_ids = [str(role.get('id')) for role in roles]
        # Удаляет старые записи, которых нет в новом списке ролей
        ProjectRate.objects.filter(project_id=project_id).exclude(role_id__in=current_role_ids).delete()
        
        for role in roles:
            pr, created = ProjectRate.objects.get_or_create(
                project_id=project_id,
                role_id=str(role.get('id')),
                defaults={
                    'project_title': project_title,
                    'role_name': role.get('name'),
                    'rate': None
                }
            )
            # Если ставка пустая, пробует подставить дефолтное значение, если оно задано
            if pr.rate is None:
                try:
                    dr = DefaultRoleRate.objects.get(role_id=str(role.get('id')))
                    if dr.default_rate is not None:
                        pr.rate = dr.default_rate
                        pr.save()
                except DefaultRoleRate.DoesNotExist:
                    pass
        rates_formset = ProjectRateFormSet(queryset=ProjectRate.objects.filter(project_id=project_id))

    if request.method == "POST":
        rates_formset = ProjectRateFormSet(request.POST, queryset=ProjectRate.objects.filter(project_id=project_id))
        return save_rates(request, rates_formset, project_id, project_title)

    context = {
        'rates_formset': rates_formset,
        'projects': projects,
        'selected_project_id': project_id,
        'selected_project_title': project_title,
    }
    return render(request, 'rates.html', context)

class ProjectRateForm(ModelForm):
    class Meta:
        model = ProjectRate
        fields = ('id', 'rate')
        widgets = {
            'id': HiddenInput(),
        }

def save_rates(request, rates_formset, project_id, project_title):
    """
    Проверяет и сохраняет ставки для проекта.
    Если все поля заполнены, сохраняет formset и возвращает redirect с сообщением об успехе.
    Если хотя бы одно поле не заполнено или форма не валидна – возвращает redirect с сообщением об ошибке.
    """
    if rates_formset.is_valid():
        all_filled = all(form.cleaned_data.get('rate') not in (None, '') for form in rates_formset)
        if all_filled:
            # print('saved: ', all_filled)
            rates_formset.save()
            messages.success(request, "Ставки для проекта сохранены.")
        else:
            
            messages.error(request, "Заполните ставки для всех ролей перед сохранением.", )
    else:
        # print("Ошибки formset:", rates_formset.errors)
        messages.error(request, "Проверьте введённые данные.")

    # Перенаправляет пользователя обратно на страницу ставок с сохранением выбранного проекта
    return redirect(f"/rates/?project_id={project_id}&project_title={project_title}")

def replace_placeholder_in_paragraph(paragraph, placeholder, replacement):
    if placeholder in paragraph.text:
        full_text = paragraph.text
        new_text = full_text.replace(placeholder, replacement)
        p = paragraph._element
        for child in list(p):
            p.remove(child)
        paragraph.add_run(new_text)

@login_required
def custom_administration(request):
    if not request.user.is_staff:
        messages.error(request, "У вас нет доступа к странице администрирования, запросите права у администратора.")
        return redirect(request.META.get('HTTP_REFERER', 'rates'))  # или другая безопасная точка входа
    admin_settings, _ = AdminSettings.objects.get_or_create(pk=1)
    settings_form = AdminSettingsForm(instance=admin_settings)
    user_form = CustomUserForm()
    
    # Запускает синхронизацию с API только для GET-запроса
    if request.method == "GET" and admin_settings.url_domain_value_id and admin_settings.api_auth_key:
        default_roles = fetch_kaiten_roles(admin_settings.url_domain_value_id, admin_settings.api_auth_key)
        api_role_ids = {str(role.get('id')) for role in default_roles}
        DefaultRoleRate.objects.exclude(role_id__in=api_role_ids).delete()
        
        for role in default_roles:
            DefaultRoleRate.objects.get_or_create(
                role_id=str(role.get('id')),
                defaults={'role_name': role.get('name')}
            )
    
    # formset для дефолтных ставок
    default_rate_formset = DefaultRoleRateFormSet(queryset=DefaultRoleRate.objects.all())
    
    if request.method == "POST":
        if 'update_settings' in request.POST:
            settings_form = AdminSettingsForm(request.POST, instance=admin_settings)
            if settings_form.is_valid():
                settings_form.save()
                messages.success(request, "Настройки успешно сохранены.")
                return redirect('custom_administration')
        elif 'create_user' in request.POST:
            user_form = CustomUserForm(request.POST)
            if user_form.is_valid():
                new_user = user_form.save(commit=False)
                new_user.set_password("defaultpassword")
                new_user.save()
                messages.success(request, "Пользователь успешно создан.")
                return redirect('custom_administration')
        elif 'save_default_rates' in request.POST:
            default_rate_formset = DefaultRoleRateFormSet(request.POST, queryset=DefaultRoleRate.objects.all())
            if default_rate_formset.is_valid():
                default_rate_formset.save()
                messages.success(request, "Стандартные ставки сохранены.")
                return redirect('custom_administration')
            else:
                # print('Ставки: ', default_rate_formset)
                messages.error(request, "Проверьте введённые данные в стандартных ставках.")

    
    context = {
        'settings_form': settings_form,
        'user_form': user_form,
        'default_rate_formset': default_rate_formset,
        'users': User.objects.all().order_by('id'),
    }
    return render(request, 'custom_administration.html', context)

@login_required
def reports_view(request):
    admin_settings, _ = AdminSettings.objects.get_or_create(pk=1)
    domain = admin_settings.url_domain_value_id
    bearer_key = admin_settings.api_auth_key

    projects = fetch_kaiten_projects(domain, bearer_key)
    roles = fetch_kaiten_roles(domain, bearer_key)
    api_role_ids = set(str(role.get('id')) for role in roles)
    for project in projects:
        project_id = str(project.get('id'))
        rates = ProjectRate.objects.filter(project_id=project_id)
        filled_rate_ids = set(str(rate.role_id) for rate in rates if rate.rate not in (None, ''))
        project['has_rates'] = (filled_rate_ids == api_role_ids)

    moscow_tz = pytz.timezone("Europe/Moscow")
    today = datetime.now(moscow_tz).date().strftime("%Y-%m-%d")

    if request.method == "POST":
        project_id = request.POST.get('project')
        template_id = request.POST.get('template')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        selected_project = next((p for p in projects if str(p.get('id')) == project_id), None)
        if not selected_project or not selected_project.get('has_rates'):
            messages.error(request, "Выбран некорректный проект или для проекта не заданы все ставки.")
        elif not template_id:
            messages.error(request, "Выберите шаблон.")
        elif not start_date or not end_date:
            messages.error(request, "Выберите начальную и конечную дату.")
        else:
            try:
                template_instance = TemplateFile.objects.get(id=template_id)
            except TemplateFile.DoesNotExist:
                messages.error(request, "Выбран некорректный шаблон.")
                return redirect('reports')
            return generate_report(request, selected_project, template_instance, start_date, end_date)

    context = {
        'projects': projects,
        'templates': TemplateFile.objects.all(),
        'today': today,
    }
    return render(request, 'reports.html', context)

def generate_report(request, project, template_instance, start_date, end_date):
    admin_settings, _ = AdminSettings.objects.get_or_create(pk=1)
    domain = admin_settings.url_domain_value_id
    bearer_key = admin_settings.api_auth_key
    billing_field_id = admin_settings.billing_custom_field_id
    billing_field_value = admin_settings.billing_custom_field_value_id

    project_id = str(project.get("id"))
    
    cards = fetch_kaiten_cards(domain, bearer_key, project_id, billing_field_id, billing_field_value)
    
    table_rows = []
    total_time = 0.0
    total_amount = 0.0
    # print(f"Получено карточек: {len(cards)}")
    for card in cards:
        card_id = card.get("id")
        card_title = card.get("title")
        time_logs = fetch_kaiten_time_logs(domain, bearer_key, card_id)
        for log in time_logs:
            created_value = log.get("created", "")
            # print(f"Лог карточки: {created_value}")
            # print(f"Лог карточки: {log}")
            # print("Установленные даты:", start_date, end_date)
            log_date_iso = created_value[:10]
            # print(f"Обработка лога: {created_value} -> {log_date_iso}")
            if start_date <= log_date_iso <= end_date:
                try:
                    minutes = float(log.get("time_spent", 0))
                except (ValueError, TypeError):
                    minutes = 0.0
                hours = minutes / 60.0
                total_time += hours

                try:
                    pr = ProjectRate.objects.get(project_id=project_id, role_id=str(log.get("role_id")))
                    rate = pr.rate if pr.rate is not None else 0
                    role_name = pr.role_name
                except ProjectRate.DoesNotExist:
                    rate = 0
                    # role_name = "Не задана ставка" 
                    role_name = "Emplyoee (Нулевая ставка)"

                amount = rate * hours
                total_amount += amount

                hours_str = f"{hours:.2f}"
                try:
                    dt = datetime.strptime(log_date_iso, "%Y-%m-%d")
                    formatted_date = dt.strftime("%d.%m.%Y")
                except Exception:
                    formatted_date = log_date_iso

                formatted_rate = f"{rate:.2f}".replace('.', ',') + " ₽"
                formatted_cost = f"{amount:.2f}".replace('.', ',') + " ₽"
                
                table_rows.append({
                    "date": formatted_date,
                    "specialist": log.get("author", {}).get("full_name", "Неизвестно"), # По требованиям нужен author, а не user?
                    "position": role_name,
                    "rate": formatted_rate,
                    "work": log.get("comment") or card_title,
                    "hours": hours_str,
                    "cost": formatted_cost,
                })

    if not table_rows:
        from django.contrib import messages
        messages.error(request, "Записей по времени в выбранном периоде в проекте не найдено")
        return redirect('reports')

    # Формат итоговых значений
    total_time_placeholder = f"{total_time:.2f} ч"
    total_amount_placeholder = f"{total_amount:.2f}".replace('.', ',') + " ₽ (" + convert_number_to_text(total_amount) + ")"


    # Работа с шаблоном документа
    doc = Document(template_instance.file.path)

    for para in doc.paragraphs:
        replace_placeholder_in_paragraph(para, "{total_time_spent}", total_time_placeholder)
        replace_placeholder_in_paragraph(para, "{total_amount_spent}", total_amount_placeholder)

    # Обработка тега {table}
    table_placeholder_found = False
    for para in doc.paragraphs:
        if "{table}" in para.text:
            full_text = para.text
            parts = full_text.split("{table}", 1)
            before_text = parts[0]
            after_text = parts[1]
            para.text = before_text.strip()
            table = doc.add_table(rows=1, cols=7)
            table.style = "Normal Table"
            set_table_borders(table)
            hdr_cells = table.rows[0].cells
            hdr_cells[0].text = "Дата"
            hdr_cells[1].text = "Специалист"
            hdr_cells[2].text = "Позиция"
            hdr_cells[3].text = "Ставка, руб."
            hdr_cells[4].text = "Содержание работ"
            hdr_cells[5].text = "Кол-во часов"
            hdr_cells[6].text = "Стоимость"
            insert_table_after(para, table)
            if after_text.strip():
                insert_paragraph_after_table(table, after_text.strip())
            for row in table_rows:
                row_cells = table.add_row().cells
                row_cells[0].text = row["date"]
                row_cells[1].text = row["specialist"]
                row_cells[1].width = Inches(1.5)
                row_cells[2].text = row["position"]
                row_cells[3].text = row["rate"]
                row_cells[4].text = row["work"]
                row_cells[4].width = Inches(3) # Расширяю столбец "Содержание работ"
                row_cells[5].text = row["hours"]
                row_cells[6].text = row["cost"]
                row_cells[6].width = Inches(1.5)
                
            table_placeholder_found = True
            break

    import io
    f_io = io.BytesIO()
    doc.save(f_io)
    f_io.seek(0)
    response = HttpResponse(
        f_io.read(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    moscow_tz = pytz.timezone("Europe/Moscow")
    today = datetime.now(moscow_tz).date().strftime("%Y-%m-%d")
    #response['Content-Disposition'] = f'attachment; filename="report_{project_id}_{start_date}_to_{end_date}.docx"'
    response['Content-Disposition'] = f'attachment; filename="report_{project_id}_{today}.docx"'
    return response