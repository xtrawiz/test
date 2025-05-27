from fastapi_admin.resources import Model
from fastapi_admin.widgets import displays, filters, inputs
from .models import User, News, Filter, Calculation, Portfolio # Import your SQLAlchemy models

class UserResource(Model):
    label = "کاربر"
    model = User
    icon = "fas fa-user"
    page_pre_title = "مدیریت کاربران"
    page_title = "کاربران"
    
    filters = [
        filters.Search(name="username", label="نام کاربری", search_mode="contains"),
        filters.Search(name="telegram_id", label="شناسه تلگرام", search_mode="equals"),
        filters.Boolean("is_pro", "کاربر Pro"),
        filters.DateRange("created_at", "تاریخ عضویت"),
    ]
    
    displays = [
        displays.Integer("id", "شناسه"),
        displays.Text("telegram_id", "شناسه تلگرام"),
        displays.Text("username", "نام کاربری"),
        displays.Text("first_name", "نام"),
        displays.Text("last_name", "نام خانوادگی"),
        displays.Boolean("is_pro", "Pro"),
        displays.Datetime("created_at", "تاریخ عضویت"),
        displays.Datetime("updated_at", "آخرین بروزرسانی"), # Assuming User model has updated_at
    ]
    
    fields = [ # Fields for create/edit forms
        "telegram_id",
        "username",
        "first_name",
        "last_name",
        "language",
        "is_pro",
        # "api_key" # Be cautious about directly editing API keys
        # created_at and updated_at are usually handled by the DB
    ]

class NewsResource(Model):
    label = "اخبار"
    model = News
    icon = "fas fa-newspaper"
    page_pre_title = "مدیریت اخبار"
    page_title = "اخبار"

    filters = [
        filters.Search(name="title", label="عنوان", search_mode="contains"),
        filters.Search(name="source", label="منبع", search_mode="contains"),
        filters.Search(name="category", label="دسته بندی", search_mode="contains"),
        filters.DateRange("published_at", "تاریخ انتشار"),
    ]

    displays = [
        displays.Integer("id", "شناسه"),
        displays.Text("title", "عنوان"),
        displays.Text("source", "منبع"),
        displays.Text("category", "دسته بندی"),
        displays.Link("link", "لینک"),
        displays.Datetime("published_at", "تاریخ انتشار"),
        displays.Datetime("created_at", "تاریخ ایجاد"),
    ]
    
    fields = [
        "source",
        "category",
        "title",
        "summary",
        "link",
        "published_at",
    ]

class FilterResource(Model):
    label = "اسکنرها"
    model = Filter
    icon = "fas fa-filter"
    page_pre_title = "مدیریت اسکنرها"
    page_title = "اسکنرها"

    filters = [
        inputs.Number("user_id", "شناسه کاربر", nullable=True), # Assuming you want to filter by internal user ID
        filters.Search(name="name", label="نام اسکنر", search_mode="contains"),
        filters.Boolean("active", "فعال"),
        filters.Search(name="timeframe", label="تایم فریم", search_mode="equals"),
    ]

    displays = [
        displays.Integer("id", "شناسه"),
        displays.Integer("user_id", "شناسه کاربر (داخلی)"), # Link to UserResource would be better if possible
        displays.Text("name", "نام اسکنر"),
        displays.Text("timeframe", "تایم فریم"),
        displays.JSON("params", "پارامترها"),
        displays.JSON("symbols", "نمادها"),
        displays.Boolean("active", "فعال"),
        displays.Datetime("last_triggered_at", "آخرین اجرا با نتیجه"),
        displays.Datetime("created_at", "تاریخ ایجاد"),
    ]

    fields = [
        "user_id", # Need a way to select user, or make it read-only if managed by bot
        "name",
        "params",
        "symbols",
        "timeframe",
        "active",
    ]


class CalculationResource(Model):
    label = "محاسبات"
    model = Calculation
    icon = "fas fa-calculator"
    page_pre_title = "مدیریت محاسبات"
    page_title = "محاسبات کاربران"

    filters = [
        inputs.Number("user_id", "شناسه کاربر", nullable=True),
        filters.Search(name="type", label="نوع محاسبه", search_mode="equals"),
        filters.DateRange("created_at", "تاریخ انجام"),
    ]

    displays = [
        displays.Integer("id", "شناسه"),
        displays.Integer("user_id", "شناسه کاربر"),
        displays.Text("type", "نوع محاسبه"),
        displays.JSON("input_params", "پارامترهای ورودی"),
        displays.JSON("result", "نتیجه"),
        displays.Datetime("created_at", "تاریخ انجام"),
    ]
    
    fields = ["user_id", "type", "input_params", "result"] # Generally, calculations might be read-only in admin


class PortfolioResource(Model):
    label = "پرتفوی"
    model = Portfolio
    icon = "fas fa-briefcase"
    page_pre_title = "مدیریت پرتفوی"
    page_title = "پرتفوی کاربران"

    filters = [
        inputs.Number("user_id", "شناسه کاربر", nullable=True),
        filters.Search(name="exchange", label="صرافی", search_mode="contains"),
        filters.Search(name="asset", label="دارایی", search_mode="contains"),
    ]

    displays = [
        displays.Integer("id", "شناسه"),
        displays.Integer("user_id", "شناسه کاربر"),
        displays.Text("exchange", "صرافی"),
        displays.Text("asset", "دارایی"),
        displays.Float("amount", "مقدار"),
        displays.Datetime("updated_at", "آخرین بروزرسانی"),
    ]

    fields = ["user_id", "exchange", "asset", "amount"] # Manage with caution, bot updates this
