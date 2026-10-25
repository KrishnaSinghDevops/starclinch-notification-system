from django.http import JsonResponse
from common.utils import db_connect, exel_query
from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
import json
from django.views.decorators.csrf import csrf_exempt
import os
import requests
from dotenv import load_dotenv
load_dotenv()
from django.contrib.auth.hashers import check_password
from types import SimpleNamespace
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse


# create fucntion without RestFull API  --> Trigger listing
@csrf_exempt
def admin_setting(request):

    data =  db_connect(""" SELECT TriggerID, TriggerCode, TriggerName, Description, IsActive FROM NotificationTrigger ORDER BY TriggerID """ )
    print(data)
    context = {
                "data" : data,
            }
    return render(request, "admin/noti_setting.html", context)

# Template API
@csrf_exempt
def noti_temp_api(request):

    if request.method == 'GET':
        data = db_connect(""" SELECT
            T.TemplateID, T.TriggerID, N.TriggerCode, N.TriggerName, T.TemplateName, T.Channel, T.EmailSubject, T.MessageBody,
            T.IsEnabled FROm NotificationTemplate T 
            INNER JOIN NotificationTrigger N
            ON T.TriggerID = N.TriggerID
            ORDER BY T.TemplateID""")
        return JsonResponse({
            "satus": True,
            "msg": "Notification template fetch sucessfully",
            "data": data,
        }, safe=True)
    else:
        return JsonResponse({
            "status": False,
            "msg": "invalid request"
        }, status = 405)


# for Template creation
@csrf_exempt
def noti_temp_manage(request):

    if request.method == "POST":

        try:
            body = json.loads(request.body)

            trigger_id = body.get("TriggerID")
            channel = body.get("Channel")
            template_name = body.get("TemplateName")
            email_subject = body.get("EmailSubject", "")
            message_body = body.get("MessageBody")
            is_enabled = body.get("IsEnabled", True)

            if not trigger_id or not channel or not template_name or not message_body:
                return JsonResponse({
                    "status": False,
                    "message": "Required fields are missing"
                }, status=400)

            exel_query(
                """
                INSERT INTO NotificationTemplate
                ( TriggerID, Channel, TemplateName, EmailSubject, MessageBody, IsEnabled )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                [ trigger_id, channel, template_name, email_subject, message_body, is_enabled ])

            return JsonResponse({
                "status": True,
                "message": "Notification template created successfully"
            }, status=201)

        except Exception as e:
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, status=500)

    else:
        return JsonResponse({
            "status": False,
            "message": "Invalid request method"
        }, status=405)


    




def send_onesignal_notification(message, user_id=None):
    app_id = os.getenv("ONESIGNAL_APP_ID")
    rest_api_key = os.getenv("ONESIGNAL_REST_API_KEY")

    if not app_id or not rest_api_key:
        return {
            "status": False,
            "message": "OneSignal credentials missing in .env"
        }

    if not user_id:
        return {
            "status": False,
            "message": "User ID is required"
        }

    # Fetch active OneSignal subscriptions for this user
    subscriptions = db_connect(
        """
        SELECT OneSignalSubscriptionID
        FROM dbo.PushSubscription
        WHERE UserID = %s
          AND IsActive = 1
          AND OneSignalSubscriptionID IS NOT NULL
        """,
        [user_id]
    )

    subscription_ids = [
        row["OneSignalSubscriptionID"]
        for row in subscriptions
        if row.get("OneSignalSubscriptionID")
    ]

    print(
        "OneSignal target UserID:",
        user_id,
        "Subscription count:",
        len(subscription_ids),
        flush=True
    )

    if not subscription_ids:
        return {
            "status": False,
            "message": "No active OneSignal subscription found for this user"
        }

    payload = {
        "app_id": app_id,
        "include_subscription_ids": subscription_ids,
        "headings": {"en": "Starclinch Notification"},
        "contents": {"en": message}
    }

    try:
        response = requests.post(
            "https://api.onesignal.com/notifications",
            headers={
                "Authorization": f"Key {rest_api_key}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=20
        )

        provider_data = response.json()

        print(
            "OneSignal response:",
            provider_data,
            flush=True
        )

        if response.ok and not provider_data.get("errors"):
            return {
                "status": True,
                "message": "Web Push request accepted by OneSignal",
                "provider_response": provider_data
            }

        return {
            "status": False,
            "message": "OneSignal rejected or could not process the notification",
            "provider_status": response.status_code,
            "provider_response": provider_data
        }

    except (requests.RequestException, ValueError) as e:
        print("OneSignal request error:", str(e), flush=True)

        return {
            "status": False,
            "message": "OneSignal request failed",
            "details": str(e)
        }


# for  edit template
@csrf_exempt
def template_update(request):

    if request.method == "PUT":

        try:
            body = json.loads(request.body)

            template_id = body.get("TemplateID")
            template_name = body.get("TemplateName")
            channel = body.get("Channel")
            email_subject = body.get("EmailSubject", "")
            message_body = body.get("MessageBody")
            is_enabled = body.get("IsEnabled", True)

            if not template_id:
                return JsonResponse({
                    "status": False,
                    "message": "TemplateID is required"
                }, status=400)

            if not template_name or not channel or not message_body:
                return JsonResponse({
                    "status": False,
                    "message": "Required fields are missing"
                }, status=400)

            rows = exel_query( """ UPDATE NotificationTemplate SET TemplateName = %s, Channel = %s, EmailSubject = %s, MessageBody = %s, IsEnabled = %s WHERE TemplateID = %s """,
                [ template_name, channel, email_subject, message_body, is_enabled, template_id ] )

            if rows == 0:
                return JsonResponse({
                    "status": False,
                    "message": "Template not found"
                }, status=404)

            return JsonResponse({
                "status": True,
                "message": "Template updated successfully"
            })

        except Exception as e:
            return JsonResponse({
                "status": False,
                "message": str(e)
            }, status=500)

    else:
        return JsonResponse({
            "status": False,
            "message": "Invalid request method"
        }, status=405)


def send_email_template(template, recipient):
    # print( "BREVO STATUS:", response.status_code, "BREVO RESPONSE:", response.text, flush=True)
    api_key = os.getenv("BREVO_API_KEY")
    sender_email = os.getenv("BREVO_FROM_EMAIL")

    if not api_key or not sender_email:
        return {
            "status": False,
            "message": "Brevo configuration missing"
        }

    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "accept": "application/json",
                "api-key": api_key,
                "content-type": "application/json"
            },
            json={
                "sender": {
                    "name": "Starclinch Notification System",
                    "email": sender_email
                },
                "to": [{"email": recipient}],
                "subject": template["EmailSubject"] or "",
                "textContent": template["MessageBody"]
            },
            timeout=20
        )

        if response.status_code not in (200, 201, 202):
            status = "FAILED"
            error = response.text[:2000]
        else:
            status = "SENT"
            error = None

        exel_query(""" INSERT INTO NotificationLog (TriggerID, TemplateID, Recipient, Channel, Status, ErrorMessage) VALUES (%s, %s, %s, %s, %s, %s) """, [
            template["TriggerID"], template["TemplateID"], recipient, "EMAIL", status, error ])

        if status == "FAILED":
            return {
                "status": False,
                "message": "Email provider rejected the request"
            }

        return {
            "status": True,
            "message": "Email accepted by provider"
        }

    except requests.RequestException:
        return {
            "status": False,
            "message": "Email provider connection failed"
        }

# imp fucn for Email delivery and brevo confrigration
@csrf_exempt
def email_notification(request):
    if request.method != "POST":
        return JsonResponse({
            "status": False,
            "message": "Invalid request method"
        }, status=405)

    try:
        body = json.loads(request.body)
        template_id = body.get("TemplateID")
        recipient = body.get("Recipient")
        if not template_id or not recipient:
            return JsonResponse({
                "status": False,
                "message": "TemplateID and Recipient are required"
            }, status=400)

        templates = db_connect(""" SELECT TemplateID, TriggerID, Channel, EmailSubject, MessageBody, IsEnabled
                                    FROM NotificationTemplate WHERE TemplateID = %s """, [template_id])
        if not templates:
            return JsonResponse({
                "status": False,
                "message": "Template not found"
            }, status=404)

        template = templates[0]

        if template["Channel"].upper() != "EMAIL":
            return JsonResponse({
                "status": False,
                "message": "Selected template is not an Email template"
            }, status=400)

        if not template["IsEnabled"]:
            return JsonResponse({
                "status": False,
                "message": "Template is disabled"
            }, status=400)

        result = send_email_template(template, recipient)

        if not result["status"]:
            return JsonResponse(result, status=502)

        return JsonResponse(result, status=200)

    except json.JSONDecodeError:
        return JsonResponse({
            "status": False,
            "message": "Invalid JSON request body"
        }, status=400)

    except Exception as e:
        print("EMAIL NOTIFICATION ERROR:", str(e), flush=True)
        return JsonResponse({
            "status": False,
            "message": "An internal error occurred"
        }, status=500)



@require_http_methods(["GET", "POST"])
def user_login(request):
    if request.method == "GET":
        return render(request, "admin/user_login.html")

    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "")

    if not username or not password:
        messages.error(request, "Username and password are required.")
        return redirect("user_login")

    users = db_connect(""" SELECT UserID, UserName, PasswordHash, Email, PhoneNumber, IsActive FROm AppUser Where UserName = %s """, [username])       

    if not users:
        messages.error(request, "Invalid username or password.")
        return redirect("user_login")
    user = users[0]
    if not user["IsActive"] or not check_password(
        password, user["PasswordHash"]
    ):
        messages.error(request, "Invalid username or password.")
        return redirect("user_login")
    request.session["user_id"] = user["UserID"]
    request.session["username"] = user["UserName"]
    request.session["user_email"] = user["Email"]
    request.session["user_phone"] = user["PhoneNumber"]
    notification_user = SimpleNamespace(
        id=user["UserID"],
        username=user["UserName"],
        email=user["Email"],
        phone=user["PhoneNumber"]
    )
    try:
        results = send_trigger_notifications("LOGIN", notification_user)
        print("LOGIN notification results:", results, flush=True)
    except Exception as e:
        print("LOGIN notification error:", str(e), flush=True)
    return redirect("user_home")


@require_http_methods(["GET", "POST"])
def user_logout(request):
    if request.method == "POST":
        user_id = request.session.get("user_id")
        username = request.session.get("username")
        email = request.session.get("user_email")
        phone = request.session.get("user_phone")
        if user_id:
            notification_user = SimpleNamespace( id=user_id, username=username, email=email,phone=phone)
            try:
                results = send_trigger_notifications( "LOGOUT", notification_user)
                print("LOGOUT notification results:", results, flush=True)
            except Exception as e:
                print("LOGOUT notification error:", str(e), flush=True)
        request.session.flush()
        return redirect("user_login")
    return redirect("user_home")

def user_home(request):
    if not request.session.get("user_id"):
        return redirect("user_login")

    return render(request, "admin/user_home.html")

# creating a fucn for fetch triggerr and using this dont need to keep hardcode tigger id

def get_enabled_notification_templates(trigger_code):
    query = """ SELECT
            t.TriggerID,
            t.TriggerCode,
            nt.TemplateID,
            nt.Channel,
            nt.TemplateName,
            nt.EmailSubject,
            nt.MessageBody
        FROM NotificationTrigger t
        INNER JOIN NotificationTemplate nt
            ON t.TriggerID = nt.TriggerID
        WHERE t.TriggerCode = %s
          AND t.IsActive = 1
          AND nt.IsEnabled = 1 """
    return db_connect(query, [trigger_code])
# dispatcher
def send_trigger_notifications(trigger_code, user):
    templates = get_enabled_notification_templates(trigger_code)
    results = []
    for template in templates:
        channel = template["Channel"].upper()
        if channel == "EMAIL":
            recipient = user.email
            if not recipient:
                results.append({
                    "channel": channel,
                    "status": False,
                    "message": "User email not available"
                })
                continue
            result = send_email_template(template, recipient)
        elif channel == "WEB_PUSH":
            result = send_onesignal_notification(
                template["MessageBody"],
                user_id=user.id
            )
            results.append({
                "channel": channel,
                "template_id": template["TemplateID"],
                **result
            })
            continue
        elif channel == "WHATSAPP":
            result = send_whatsapp_template(
                template,
                recipient_phone=getattr(user, "phone", None)
            )

            results.append({
                "channel": channel,
                "template_id": template["TemplateID"],
                **result
            })
            continue
        else:
            results.append({
                "channel": channel,
                "status": False,
                "message": "Unsupported notification channel"
            })
            continue
        results.append({
            "channel": channel,
            "template_id": template["TemplateID"],
            **result
        })
    return results
# worker
def onesignal_service_worker(request):
    worker_code = (
        'importScripts("https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.sw.js");'
    )
    return HttpResponse(
        worker_code,
        content_type="application/javascript"
    )                 
            
from django.views.decorators.http import require_POST
@require_POST
def save_push_suscribtion(request):
    user_id = request.session.get("user_id")
    print("SAVE PUSH FUNCTION CALLED", flush=True)
    print("User ID:", user_id, flush=True)
    if not user_id:
        return JsonResponse(
            {"status": False, "msg": "Login required"},
            status=401
        )
    try:
        data = json.loads(request.body)
        subscription_id = data.get("subscription_id")

        print("Received subscription ID:", subscription_id, flush=True)

        if not subscription_id:
            return JsonResponse(
                {"status": False, "msg": "Subscription ID missing"},
                status=400
            )
        existing = db_connect( """ SELECT SubscriptionID FROM dbo.PushSubscription WHERE UserID = %s AND OneSignalSubscriptionID = %s """,
            [user_id, subscription_id] )
        if existing:
            exel_query( """ UPDATE dbo.PushSubscription SET IsActive = 1 WHERE UserID = %s AND OneSignalSubscriptionID = %s
                """, [user_id, subscription_id] )
            print("Existing subscription activated", flush=True)
        else:
            exel_query(""" INSERT INTO dbo.PushSubscription (UserID, OneSignalSubscriptionID, IsActive) VALUES (%s, %s, 1) """, [user_id, subscription_id] )
            print("New subscription inserted", flush=True)
        saved_rows = db_connect(""" SELECT UserID, OneSignalSubscriptionID, IsActive  FROM dbo.PushSubscription WHERE UserID = %s  AND OneSignalSubscriptionID = %s """, [user_id, subscription_id])
        print("Saved subscription rows:", saved_rows, flush=True)
        return JsonResponse({
            "status": True,
            "msg": "Subscription saved",
            "saved_rows": saved_rows
        })
    except Exception as e:
        print("SAVE PUSH ERROR:", str(e), flush=True)
        return JsonResponse(
            {"status": False, "msg": str(e)},
            status=500
        )



# function for whatsapp

def send_whatsapp_template(template, recipient_phone):
    mock_mode = os.getenv(
        "WHATSAPP_MOCK_MODE", "True"
    ).strip().lower() in ("true", "1", "yes")
    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    phone_number_id = os.getenv("PHONE_NUMBER_ID")
    api_version = os.getenv("WHATSAPP_API_VERSION", "v23.0")
    if not recipient_phone:
        return {
            "status": False,
            "message": "Recipient phone number is missing"
        }
    # TemplateName must match an approved Meta template name.
    template_name = (template.get("TemplateName") or "").strip()
    if not template_name:
        return {
            "status": False,
            "message": "WhatsApp template name is missing"
        }

    # No real API request in mock mode.
    if mock_mode:
        return {
            "status": True,
            "mode": "MOCK",
            "message": "Mock only: WhatsApp payload prepared; no message sent",
            "recipient": recipient_phone,
            "template_name": template_name
        }

    if not access_token or not phone_number_id:
        return {
            "status": False,
            "message": "WhatsApp credentials are missing in .env"
        }

    # Cloud API expects the recipient number with country code.
    recipient = "".join(
        char for char in str(recipient_phone) if char.isdigit()
    )

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {
                "code": "en_US"
            }
        }
    }

    url = (
        f"https://graph.facebook.com/"
        f"{api_version}/{phone_number_id}/messages"
    )

    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=20
        )

        try:
            provider_data = response.json()
        except ValueError:
            provider_data = {"response": response.text[:1000]}

        if response.ok and provider_data.get("messages"):
            return {
                "status": True,
                "mode": "LIVE",
                "message": "WhatsApp request accepted by Meta",
                "provider_response": provider_data
            }

        return {
            "status": False,
            "mode": "LIVE",
            "message": "WhatsApp API rejected the request",
            "provider_status": response.status_code,
            "provider_response": provider_data
        }

    except requests.RequestException as exc:
        return {
            "status": False,
            "mode": "LIVE",
            "message": "WhatsApp API request failed",
            "details": str(exc)
        }


@csrf_exempt
def whatsapp_notification(request):
    if request.method != "POST":
        return JsonResponse({
            "status": False,
            "message": "Invalid request method"
        }, status=405)

    try:
        body = json.loads(request.body)
        template_id = body.get("TemplateID")
        recipient = body.get("Recipient")

        if not template_id or not recipient:
            return JsonResponse({
                "status": False,
                "message": "TemplateID and Recipient are required"
            }, status=400)

        templates = db_connect(""" SELECT TemplateID, TriggerID, Channel, TemplateName, EmailSubject, MessageBody, IsEnabled  FROM NotificationTemplate WHERE TemplateID = %s """, [template_id])

        if not templates:
            return JsonResponse({
                "status": False,
                "message": "Template not found"
            }, status=404)
        template = templates[0]
        if (template.get("Channel") or "").upper() != "WHATSAPP":
            return JsonResponse({
                "status": False,
                "message": "Selected template is not a WhatsApp template"
            }, status=400)
        if not template.get("IsEnabled"):
            return JsonResponse({
                "status": False,
                "message": "Template is disabled"
            }, status=400)
        result = send_whatsapp_template(template, recipient)
        # Record mock/live attempt in NotificationLog.
        status_value = (
            "MOCK" if result.get("mode") == "MOCK"
            and result.get("status") else
            "SENT" if result.get("status") else "FAILED"
        )
        error_message = (
            None if result.get("status")
            else result.get("message", "WhatsApp request failed")
        )
        exel_query(""" INSERT INTO NotificationLog (TriggerID, TemplateID, Recipient, Channel, Status, ErrorMessage)
            VALUES (%s, %s, %s, %s, %s, %s) """, [ template["TriggerID"], template["TemplateID"], recipient, "WHATSAPP", status_value, error_message  ])

        return JsonResponse(
            result,
            status=200 if result.get("status") else 502
        )

    except json.JSONDecodeError:
        return JsonResponse({
            "status": False,
            "message": "Invalid JSON request body"
        }, status=400)

    except Exception as e:
        print("WHATSAPP NOTIFICATION ERROR:", str(e), flush=True)
        return JsonResponse({
            "status": False,
            "message": "Internal error while processing WhatsApp notification"
        }, status=500)



@csrf_exempt
@require_http_methods(["POST"])
def web_push_notification(request):
    """
    Admin Test Send API for WEB_PUSH templates.
    Request JSON: {"TemplateID": 3, "UserID": 1}
    """
    try:
        body = json.loads(request.body or "{}")
        template_id = body.get("TemplateID")
        user_id = body.get("UserID")

        if not template_id or not user_id:
            return JsonResponse({
                "status": False,
                "message": "TemplateID and UserID are required"
            }, status=400)

        rows = db_connect("""
            SELECT TemplateID, TriggerID, Channel, TemplateName,
                   EmailSubject, MessageBody, IsEnabled
            FROM NotificationTemplate
            WHERE TemplateID = %s
        """, [template_id])

        if not rows:
            return JsonResponse({
                "status": False,
                "message": "Template not found"
            }, status=404)

        template = rows[0]

        if (template.get("Channel") or "").upper() != "WEB_PUSH":
            return JsonResponse({
                "status": False,
                "message": "Selected template is not a Web Push template"
            }, status=400)

        if not template.get("IsEnabled"):
            return JsonResponse({
                "status": False,
                "message": "Template is disabled. Enable it before testing."
            }, status=400)

        result = send_onesignal_notification(
            template["MessageBody"],
            user_id=int(user_id)
        )

        log_status = "SENT" if result.get("status") else "FAILED"
        log_error = None if result.get("status") else result.get(
            "message", "Web Push request failed"
        )

        exel_query("""
            INSERT INTO NotificationLog
                (TriggerID, TemplateID, Recipient, Channel, Status, ErrorMessage)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, [
            template["TriggerID"],
            template["TemplateID"],
            str(user_id),
            "WEB_PUSH",
            log_status,
            log_error
        ])

        return JsonResponse(
            result,
            status=200 if result.get("status") else 502
        )

    except (ValueError, TypeError):
        return JsonResponse({
            "status": False,
            "message": "TemplateID and UserID must be valid numbers"
        }, status=400)

    except json.JSONDecodeError:
        return JsonResponse({
            "status": False,
            "message": "Invalid JSON request body"
        }, status=400)

    except Exception as exc:
        print("WEB PUSH TEST ERROR:", str(exc), flush=True)
        return JsonResponse({
            "status": False,
            "message": "Web Push test failed due to a server error"
        }, status=500)
