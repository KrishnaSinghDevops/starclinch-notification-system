from django.urls import path
from adminpanel.views import *

urlpatterns = [
    # for admin page
    path("admin_dashboard", admin_setting, name = "notification_setting"),
    # Templates fetching
    path("noti_temp", noti_temp_api, name="notification_template"),
    # Template create/manage karna
    path("noti/temp/manage", noti_temp_manage, name="template manage"),
    path("update_template", template_update, name="update_template"),

    # for email test
    path("email_noti_sending", email_notification, name="send_email"),


    path("login_user", user_login, name="user_login"),
    path("logout_user", user_logout, name="user_logout"),
    path("user_home", user_home, name="user_home"),


    # for webpush
    path("OneSignalSDKWorker.js", onesignal_service_worker, name="onesignal_service_worker"),
    path("save_one_suscrip", save_push_suscribtion, name="save_push_suscribtion"),


    # whatsapp
    path("whatsapp_noti_sending", whatsapp_notification, name="send_whatsapp"),
    
    # Web Push test-send API
    path(
        "webpush_noti_sending",
        web_push_notification,
        name="send_web_push"
    ),


]



