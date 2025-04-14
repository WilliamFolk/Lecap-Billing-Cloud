import requests
import io
import logging
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.shortcuts import render, redirect
from django.conf import settings
from django.utils import timezone
from django import forms
from accounts.models import AdminSettings
from .models import  ProjectRate, DefaultRoleRate
from accounts.forms import AdminSettingsForm, CustomUserForm
from LecapProject.kaiten_api import fetch_kaiten_roles, fetch_kaiten_projects, fetch_kaiten_cards, fetch_kaiten_time_logs, fetch_kaiten_boards
from django.forms import modelformset_factory, ModelForm, HiddenInput
from datetime import datetime, timedelta
import pytz
from django.http import HttpResponse, JsonResponse
from docx import Document
from docxTemplate.models import TemplateFile
from docxTemplate.views import insert_table_after, set_table_borders, insert_paragraph_after_table, convert_number_to_text
from django.forms import ModelForm, HiddenInput
from .models import ProjectRate
from .forms import DefaultRoleRateFormSet
from docx.shared import Inches, Pt
from django.db.models.functions import Cast
from django.db.models import CharField
from urllib.parse import urlencode
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH

logger = logging.getLogger('kaiten')

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

def check_board_rates(board, project_id, roles):
    """
    Функция проверяет, удовлетворяет ли доска условию наличия ставок для каждой роли.
    Если для роли отсутствует кастомная ставка, ищется дефолтная ставка.
    Возвращает:
      - board_valid: True, если для всех ролей найдена ставка (кастомная или дефолтная);
      - auto_used: True, если хотя бы для одной роли ставка берётся из дефолтных.
    """
    board_valid = True
    auto_used = False
    board_id = board.get("id")
    for role in roles:
        role_id = str(role.get("id"))
        try:
            pr = ProjectRate.objects.get(
                project_id=project_id,
                board_id=board_id,
                role_id=role_id
            )
            if pr.rate is None:
                try:
                    dr = DefaultRoleRate.objects.get(role_id=role_id)
                    if dr.default_rate is not None:
                        auto_used = True
                    else:
                        board_valid = False
                        break
                except DefaultRoleRate.DoesNotExist:
                    board_valid = False
                    break
        except ProjectRate.DoesNotExist:
            try:
                dr = DefaultRoleRate.objects.get(role_id=role_id)
                if dr.default_rate is not None:
                    auto_used = True
                else:
                    board_valid = False
                    break
            except DefaultRoleRate.DoesNotExist:
                board_valid = False
                break
    return board_valid, auto_used

@login_required
def get_boards(request):
    kaiten_api_down = False
    space_id = request.GET.get('space_id')
    for_report = request.GET.get('for_report') == "1"
    admin_settings, _ = AdminSettings.objects.get_or_create(pk=1)
    domain = admin_settings.url_domain_value_id
    bearer_key = admin_settings.api_auth_key

    boards = fetch_kaiten_boards(domain, bearer_key, space_id)
    if not boards:
        kaiten_api_down = True

    if for_report:
        roles = fetch_kaiten_roles(domain, bearer_key)
        if not roles:
            kaiten_api_down = True
        for board in boards:
            valid, auto_used = check_board_rates(board, space_id, roles)
            board["has_rates"] = valid
            if valid and auto_used:
                board["title"] += " (автоставки)"
    
    # Для AJAX‑ответа можно вернуть ошибку прямо в JSON
    error_message = ""
    if kaiten_api_down:
        error_message = "Сервер Kaiten недоступен. Пожалуйста, повторите попытку позже."
    return JsonResponse({"boards": boards, "error": error_message})


@login_required
def rates_view(request):
    admin_settings, _ = AdminSettings.objects.get_or_create(pk=1)
    domain = admin_settings.url_domain_value_id
    bearer_key = admin_settings.api_auth_key

    # Флаг для ошибки подключения к API
    kaiten_api_down = False

    if domain and bearer_key:
        # Получение дефолтных ролей
        default_roles = fetch_kaiten_roles(domain, bearer_key)
        if not default_roles:
            kaiten_api_down = True
        else:
            api_role_ids = {str(role.get('id')) for role in default_roles}
            for role in default_roles:
                obj, created = DefaultRoleRate.objects.get_or_create(
                    role_id=str(role.get('id')),
                    defaults={'role_name': role.get('name')}
                )
                if not created and obj.role_name != role.get('name'):
                    obj.role_name = role.get('name')
                obj.last_sync = timezone.now()
                obj.save()
            DefaultRoleRate.objects.filter(last_sync__lt=timezone.now() - timedelta(days=7))\
                .exclude(role_id__in=api_role_ids)\
                .delete()

        # Получение проектов
        projects = fetch_kaiten_projects(domain, bearer_key)
        if not projects:
            kaiten_api_down = True
    else:
        projects = []

    # Выбор проекта и доски
    project_id = request.GET.get('project_id')
    project_title = request.GET.get('project_title', '')
    board_id = request.GET.get('board_id')
    board_title = request.GET.get('board_title', '')

    if project_id and not project_title:
        for project in projects:
            if str(project['id']) == str(project_id):
                project_title = project['title']
                break
    if not project_id and projects:
        project_id = str(projects[0]['id'])
        project_title = projects[0]['title']

    boards = []
    if project_id:
        boards = fetch_kaiten_boards(domain, bearer_key, project_id)
        if not boards:
            kaiten_api_down = True
        if boards and not board_id:
            board_id = boards[0]['id']
            board_title = boards[0]['title']

    # Работа с формсетом ставок
    ProjectRateFormSet = modelformset_factory(ProjectRate, form=ProjectRateForm, extra=0)
    rates_formset = None

    if project_id and board_id:
        roles = fetch_kaiten_roles(domain, bearer_key)
        if not roles:
            kaiten_api_down = True
        current_role_ids = [str(role.get("id")) for role in roles]

        # Обновление/создание объектов ProjectRate
        for role in roles:
            obj, created = ProjectRate.objects.get_or_create(
                project_id=project_id,
                board_id=board_id,
                role_id=str(role.get('id')),
                defaults={
                    'project_title': project_title,
                    'board_title': board_title,
                    'role_name': role.get('name'),
                    'rate': None
                }
            )
            obj.last_sync = timezone.now()
            if obj.project_title != project_title or obj.board_title != board_title or obj.role_name != role.get('name'):
                obj.project_title = project_title
                obj.board_title = board_title
                obj.role_name = role.get('name')
            obj.save()
            
        ProjectRate.objects.filter(project_id=project_id, board_id=board_id)\
            .exclude(role_id__in=current_role_ids)\
            .filter(last_sync__lt=timezone.now() - timedelta(days=7))\
            .delete()

        rates_formset = ProjectRateFormSet(queryset=ProjectRate.objects.filter(project_id=project_id, board_id=board_id))

    if kaiten_api_down:
        messages.error(request, "Сервер Kaiten недоступен. Пожалуйста, повторите попытку позже.")

    if request.method == "POST":
        if 'save_default_rates' in request.POST:
            default_rate_formset = DefaultRoleRateFormSet(request.POST, queryset=DefaultRoleRate.objects.all())
            if default_rate_formset.is_valid():
                changed = any(form.has_changed() for form in default_rate_formset.forms)
                if changed:
                    for instance in default_rate_formset.save(commit=False):
                        instance.save()
                messages.success(request, "Стандартные ставки сохранены.")
            else:
                messages.error(request, "Проверьте введённые данные в стандартных ставках.")
            params = {
                'project_id': project_id,
                'project_title': project_title,
                'board_id': board_id,
                'board_title': board_title,
            }
            return redirect(f"/rates/?{urlencode(params)}")
        else:
            rates_formset = ProjectRateFormSet(
                request.POST, 
                queryset=ProjectRate.objects.filter(project_id=project_id, board_id=board_id)
            )
            return save_rates(request, rates_formset, project_id, project_title, board_id, board_title)

    context = {
        'rates_formset': rates_formset,
        'projects': projects,
        'boards': boards,
        'selected_project_id': project_id,
        'selected_project_title': project_title,
        'selected_board_id': board_id,
        'selected_board_title': board_title,
        'default_rate_formset': DefaultRoleRateFormSet(queryset=DefaultRoleRate.objects.all()),
    }
    return render(request, 'rates.html', context)


class ProjectRateForm(forms.ModelForm):
    rate = forms.IntegerField(required=False, widget=forms.NumberInput(), label="Почасовая ставка")

    class Meta:
        model = ProjectRate
        fields = ('id', 'rate', 'project_id', 'board_id')
        widgets = {
            'id': forms.HiddenInput(),
            'project_id': forms.HiddenInput(),
            'board_id': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_default = False
        if self.instance and self.instance.rate is None:
            try:
                dr = DefaultRoleRate.objects.get(role_id=self.instance.role_id)
                if dr.default_rate is not None:
                    self.initial['rate'] = dr.default_rate
                    self.is_default = True
            except DefaultRoleRate.DoesNotExist:
                pass

    def has_changed(self):
        if getattr(self, 'is_default', False):
            return True
        return super().has_changed()

    def clean_rate(self):
        data = self.cleaned_data.get('rate')
        if data == '':
            return None
        return data

def save_rates(request, rates_formset, project_id, project_title, board_id, board_title):
    """
    Валидирует и сохраняет ставки для проекта. Если все поля заполнены, сохраняет formset и перенаправляет с сообщениет об успехе.
    Если какие-либо ставки не заполнены или форма не валидна, возвращает redirect с сообщением об ошибке.
    """
    if rates_formset.is_valid():
        all_filled = all(form.cleaned_data.get('rate') not in (None, '') for form in rates_formset)
        if all_filled:
            rates_formset.save()
            messages.success(request, "Ставки для проекта сохранены.")
        else:
            messages.error(request, "Заполните ставки для всех ролей перед сохранением.")
    else:
        messages.error(request, "Проверьте введённые данные.")
    
    params = {
        'project_id': project_id,
        'project_title': project_title,
        'board_id': board_id,
        'board_title': board_title,
    }
    return redirect(f"/rates/?{urlencode(params)}")


def set_cell_text(cell, text):
    paragraph = cell.paragraphs[0]
    for run in paragraph.runs:
        run.text = ""
    run = paragraph.add_run(text)
    # Сбрасывает отступы
    paragraph.paragraph_format.left_indent = 0
    paragraph.paragraph_format.first_line_indent = 0


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
        return redirect(request.META.get('HTTP_REFERER', 'rates'))
        
    admin_settings, _ = AdminSettings.objects.get_or_create(pk=1)
    settings_form = AdminSettingsForm(instance=admin_settings)
    user_form = CustomUserForm()
    
    kaiten_api_down = False  # Флаг для отслеживания ошибки подключения к Kaiten

    # Синхронизация с API только для GET-запроса
    if request.method == "GET" and admin_settings.url_domain_value_id and admin_settings.api_auth_key:
        default_roles = fetch_kaiten_roles(admin_settings.url_domain_value_id, admin_settings.api_auth_key)
        if not default_roles:
            kaiten_api_down = True
        else:
            api_role_ids = {str(role.get('id')) for role in default_roles}
            DefaultRoleRate.objects.exclude(role_id__in=api_role_ids).delete()
            for role in default_roles:
                DefaultRoleRate.objects.get_or_create(
                    role_id=str(role.get('id')),
                    defaults={'role_name': role.get('name')}
                )
    # Вывод сообщения об ошибке, если API недоступен
    if kaiten_api_down:
        messages.error(request, "Сервер Kaiten недоступен. Пожалуйста, повторите попытку позже.")

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
                password = user_form.cleaned_data.get('password')
                if password:
                    new_user.set_password(password)
                else:
                    new_user.set_password("defaultpassword")
                new_user.save()
                messages.success(request, "Пользователь успешно создан.")
                return redirect('custom_administration')
            else:
                for field, errors in user_form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field.capitalize()}: {error}")
                return redirect('custom_administration')
        elif 'save_default_rates' in request.POST:
            default_rate_formset = DefaultRoleRateFormSet(request.POST, queryset=DefaultRoleRate.objects.all())
            if default_rate_formset.is_valid():
                default_rate_formset.save()
                messages.success(request, "Стандартные ставки сохранены.")
                return redirect('custom_administration')
            else:
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
    kaiten_api_down = False
    admin_settings, _ = AdminSettings.objects.get_or_create(pk=1)
    domain = admin_settings.url_domain_value_id
    bearer_key = admin_settings.api_auth_key

    projects = fetch_kaiten_projects(domain, bearer_key)
    if not projects:
        kaiten_api_down = True

    roles = fetch_kaiten_roles(domain, bearer_key)
    if not roles:
        kaiten_api_down = True

    for project in projects:
        project_id = str(project.get('id'))
        boards = fetch_kaiten_boards(domain, bearer_key, project_id)
        if not boards:
            kaiten_api_down = True
        valid_board_exists = False
        for board in boards:
            valid, auto_used = check_board_rates(board, project_id, roles)
            board["has_rates"] = valid
            if valid and auto_used:
                board["title"] += " (автоставки)"
            if valid:
                valid_board_exists = True
        project['has_rates'] = valid_board_exists

    moscow_tz = pytz.timezone("Europe/Moscow")
    today = datetime.now(moscow_tz).date().strftime("%Y-%m-%d")

    if request.method == "POST":
        project_id = request.POST.get('project')
        board_id = request.POST.get('board')
        template_id = request.POST.get('template')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        selected_project = next((p for p in projects if str(p.get('id')) == project_id), None)
        if not selected_project or not selected_project.get('has_rates'):
            messages.error(request, "Выбран некорректный проект или для проекта не заданы ставки ни для одной доски.")
        elif not board_id:
            messages.error(request, "Выберите доску.")
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
            return generate_report(request, selected_project, template_instance, start_date, end_date, board_id)

    if kaiten_api_down:
        messages.error(request, "Сервер Kaiten недоступен. Пожалуйста, повторите попытку позже.")

    context = {
        'projects': projects,
        'today': today,
        'templates': TemplateFile.objects.all(),
    }
    return render(request, 'reports.html', context)


def generate_report(request, project, template_instance, start_date, end_date, board_id):
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
    for card in cards:
        card_id = card.get("id")
        card_title = card.get("title")
        time_logs = fetch_kaiten_time_logs(domain, bearer_key, card_id)
        for log in time_logs:
            log_date_iso = log.get("created", "")[:10]
            if start_date <= log_date_iso <= end_date:
                try:
                    minutes = float(log.get("time_spent", 0))
                except (ValueError, TypeError):
                    minutes = 0.0
                hours = minutes / 60.0
                total_time += hours

                try:
                    pr = ProjectRate.objects.get(
                        project_id=project_id,
                        board_id=board_id,
                        role_id=str(log.get("role_id"))
                    )
                    if pr.rate is not None:
                        rate = pr.rate
                    else:
                        try:
                            dr = DefaultRoleRate.objects.get(role_id=str(log.get("role_id")))
                            rate = dr.default_rate if dr.default_rate is not None else 0
                        except DefaultRoleRate.DoesNotExist:
                            rate = 0
                    role_name = pr.role_name
                except ProjectRate.DoesNotExist:
                    try:
                        dr = DefaultRoleRate.objects.get(role_id=str(log.get("role_id")))
                        rate = dr.default_rate if dr.default_rate is not None else 0
                        role_name = dr.role_name
                    except DefaultRoleRate.DoesNotExist:
                        rate = 0
                        role_name = "Employee (Нулевая ставка)"

                amount = rate * hours
                total_amount += amount

                hours_str = f"{hours:.2f}".replace('.', ',')
                try:
                    dt = datetime.strptime(log_date_iso, "%Y-%m-%d")
                    formatted_date = dt.strftime("%d.%m.%Y")
                except Exception:
                    formatted_date = log_date_iso

                formatted_rate = f"{rate:.2f}".replace('.', ',') + " ₽"
                formatted_cost = f"{amount:.2f}".replace('.', ',') + " ₽"
                
                table_rows.append({
                    "date": formatted_date,
                    "date_iso": log_date_iso,  # ключ для сортировки
                    "specialist": log.get("author", {}).get("full_name", "Неизвестно"),
                    "position": role_name,
                    "rate": formatted_rate,
                    "work": log.get("comment") or card_title,
                    "hours": hours_str,
                    "cost": formatted_cost,
                })

    if not table_rows:
        messages.error(request, "Записей по времени в выбранном периоде в проекте не найдено")
        return redirect('reports')
    table_rows.sort(key=lambda row: row["date_iso"])

    total_time_placeholder = f"{total_time:.2f} ч"
    total_amount_placeholder = f"{total_amount:.2f}".replace('.', ',') + " ₽ (" + convert_number_to_text(total_amount) + ")"

    # Работа с шаблоном документа
    doc = Document(template_instance.file.path)
    for para in doc.paragraphs:
        replace_placeholder_in_paragraph(para, "{total_time_spent}", total_time_placeholder)
        replace_placeholder_in_paragraph(para, "{total_amount_spent}", total_amount_placeholder)
    
    # Поиск и замена тега {table} в документе
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
                set_cell_text(row_cells[0], row["date"])
                row_cells[0].width = Inches(1.2)
                row_cells[1].text = row["specialist"]
                row_cells[1].width = Inches(2)
                row_cells[2].text = row["position"]
                row_cells[2].width = Inches(1.5)
                row_cells[3].text = row["rate"]
                row_cells[3].width = Inches(2.5)
                row_cells[4].text = row["work"]
                row_cells[4].width = Inches(3.5)
                row_cells[5].text = row["hours"]
                row_cells[5].width = Inches(1.2)
                row_cells[6].text = row["cost"]
                row_cells[6].width = Inches(1.5)
            table_placeholder_found = True
            break
    for i, row in enumerate(table.rows):
        for j, cell in enumerate(row.cells):
            cell.vertical_alignment = WD_ALIGN_VERTICAL.BOTTOM
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                paragraph.paragraph_format.line_spacing = 1
                paragraph.paragraph_format.space_before = Pt(0)
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.paragraph_format.left_indent = 0
                paragraph.paragraph_format.first_line_indent = 0
                for run in paragraph.runs:
                    run.font.size = Pt(11)
                    if i == 0:
                        run.font.bold = True
                    elif j == 0:
                        run.font.bold = True
    f_io = io.BytesIO()
    doc.save(f_io)
    f_io.seek(0)
    response = HttpResponse(
        f_io.read(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    moscow_tz = pytz.timezone("Europe/Moscow")
    today = datetime.now(moscow_tz).date().strftime("%Y-%m-%d")
    response['Content-Disposition'] = f'attachment; filename="report_{project_id}_{today}.docx"'
    return response
