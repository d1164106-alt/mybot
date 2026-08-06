import os
import json
import asyncio
import re
import datetime
import time
import threading
import random
import hashlib

from telethon import events
from telethon import TelegramClient, Button
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.types import Channel, ChatInviteAlready
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.sessions import StringSession

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice

API_ID = 22651991
API_HASH = 'ecad214ecff6a5cd90fc141d4e32f597'
BOT_TOKEN = "8183432789:AAFYu5ZKxS4bhr7Hy7kWdvANBA4MRZEkdHs"
REG_ID = 1724716
REG_HASH = '00b2d8f59c12c1b9a4bc63b70b461b2f'
PAY_TOKEN = "284685063:TEST:300f86a2-ddc1-460d-85a2-0d5854611a51"

ACC_FILE = 'registered_accounts.json'
NUM_FILE = 'numbers_for_sale.json'
USER_FILE = 'user_data.json'
CONF_FILE = 'bot_settings.json'
FORCE_SUB_FILE = 'force_sub_channels.json'
BROADCAST_FILE = 'broadcast_messages.json'
POINT_LINKS_FILE = 'point_links.json'
VERIFIED_USERS_FILE = 'verified_users.json'
USER_LOG_FILE = 'user_login_log.json'

client = TelegramClient('BotSession', API_ID, API_HASH)
bot = telebot.TeleBot(BOT_TOKEN)
pay_token = PAY_TOKEN

u_clients = {}
code_reqs = {}
res_timers = {}
u_sessions = {}
avail_nums = {}
syyad_users = {}
point_links = {}
force_sub_channels = {}
broadcast_messages = {}
verified_users = {}
user_verifications = {}
broadcast_texts = {}
user_login_log = {}

syyad_conf = {
    'admin_ids': [],
    'dailyGiftPoints': 0,
    'referralPoints': 0,
    'chargeRates': [],
    'reservationTimeoutMinutes': 60,
    'publish_channel_id': None,
    'verification_enabled': True,
    'referral_campaign_enabled': False,
    'referral_campaign_points': 0,
    'referral_campaign_users': 0,
    'max_referrals_per_user': 0,
    'owner_id': None,
    'force_sub_enabled': True
}

def load(fpath, d_val):
    if os.path.exists(fpath):
        with open(fpath, 'r', encoding='utf-8') as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return d_val
    return d_val

def save(fpath, data):
    with open(fpath, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

def load_all():
    global u_sessions, avail_nums, syyad_users, syyad_conf, force_sub_channels, broadcast_messages, point_links, verified_users, user_login_log
    u_sessions = load(ACC_FILE, {})
    avail_nums = load(NUM_FILE, {})
    syyad_users = load(USER_FILE, {})
    loaded_settings = load(CONF_FILE, {})
    force_sub_channels = load(FORCE_SUB_FILE, {})
    broadcast_messages = load(BROADCAST_FILE, {})
    point_links = load(POINT_LINKS_FILE, {})
    verified_users = load(VERIFIED_USERS_FILE, {})
    user_login_log = load(USER_LOG_FILE, {})

    syyad_conf.update(loaded_settings)
    
    if not syyad_conf.get('owner_id'):
        syyad_conf['owner_id'] = '541029541'
    
    if syyad_conf['owner_id'] not in syyad_conf['admin_ids']:
        syyad_conf['admin_ids'].append(syyad_conf['owner_id'])

def save_all():
    save(ACC_FILE, u_sessions)
    save(NUM_FILE, avail_nums)
    save(CONF_FILE, syyad_conf)
    save(USER_FILE, syyad_users)
    save(FORCE_SUB_FILE, force_sub_channels)
    save(BROADCAST_FILE, broadcast_messages)
    save(POINT_LINKS_FILE, point_links)
    save(VERIFIED_USERS_FILE, verified_users)
    save(USER_LOG_FILE, user_login_log)

def get_syyad_bal(uid):
    uid_str = str(uid)
    if uid_str not in syyad_users:
        syyad_users[uid_str] = {
            'points': 0,
            'stars': 0,
            'lastDailyGiftClaim': None,
            'old_numbers': [],
            'new_numbers': [],
            'referred_by': None,
            'referral_count': 0,
            'total_earned_from_referrals': 0,
            'daily_ranking': 0,
            'force_sub_checked': False,
            'verified': False
        }

    syyad_users[uid_str].setdefault('points', 0)
    syyad_users[uid_str].setdefault('stars', 0)
    syyad_users[uid_str].setdefault('lastDailyGiftClaim', None)
    syyad_users[uid_str].setdefault('old_numbers', [])
    syyad_users[uid_str].setdefault('new_numbers', [])
    syyad_users[uid_str].setdefault('referred_by', None)
    syyad_users[uid_str].setdefault('referral_count', 0)
    syyad_users[uid_str].setdefault('total_earned_from_referrals', 0)
    syyad_users[uid_str].setdefault('daily_ranking', 0)
    syyad_users[uid_str].setdefault('force_sub_checked', False)
    syyad_users[uid_str].setdefault('verified', False)

    save(USER_FILE, syyad_users)
    return syyad_users[uid_str]

def is_adm(uid):
    return str(uid) in syyad_conf['admin_ids']

def is_owner(uid):
    return str(uid) == str(syyad_conf.get('owner_id'))

def mask_phone_number(phone, full_show=False):
    if not phone:
        return phone
    
    if full_show:
        return phone
    
    if len(phone) <= 3:
        return phone
    visible = phone[:3]
    masked = '*' * (len(phone) - 3)
    return visible + masked

async def get_user_info(user_id):
    try:
        user_entity = await client.get_entity(int(user_id))
        return {
            'id': user_entity.id,
            'username': user_entity.username,
            'first_name': user_entity.first_name,
            'last_name': user_entity.last_name
        }
    except:
        return {
            'id': user_id,
            'username': None,
            'first_name': f"مستخدم {user_id}",
            'last_name': None
        }

async def log_user_login(user_id, username, first_name, last_name=None):
    uid_str = str(user_id)
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    user_info = {
        'user_id': uid_str,
        'username': username or 'لا يوجد',
        'first_name': first_name or 'لا يوجد',
        'last_name': last_name or 'لا يوجد',
        'login_time': current_time,
        'full_name': f"{first_name or ''} {last_name or ''}".strip() or 'مستخدم مجهول'
    }
    
    if uid_str not in user_login_log:
        user_login_log[uid_str] = []
    
    user_login_log[uid_str].append(user_info)
    
    if len(user_login_log[uid_str]) > 50:
        user_login_log[uid_str] = user_login_log[uid_str][-50:]
    
    save(USER_LOG_FILE, user_login_log)
    
    admin_message = (
        f"👤 **دخول مستخدم جديد إلى البوت**\n\n"
        f"🆔 **الآيدي:** `{uid_str}`\n"
        f"👤 **الاسم:** {user_info['full_name']}\n"
        f"📛 **اليوزر:** @{username}" if username else "📛 **اليوزر:** لا يوجد\n"
        f"🕐 **الوقت:** {current_time}\n"
        f"📊 **إجمالي المستخدمين:** {len(syyad_users)}"
    )
    
    for admin_id in syyad_conf['admin_ids']:
        try:
            await client.send_message(int(admin_id), admin_message, parse_mode='markdown')
        except:
            pass

async def send_welcome_message(user_id, user_info):
    welcome_msg = (
        f"🎉 **أهلاً بك في بوت شراء الأرقام!**\n\n"
        f"👤 مرحباً {user_info.get('first_name', '')}!\n\n"
        f"📌 **مميزات البوت:**\n"
        f"• شراء أرقام مميزة\n"
        f"• نظام نقاط ومكافآت\n"
        f"• هدية يومية مجانية\n"
        f"• نظام إحالات للحصول على نقاط إضافية\n\n"
        f"🔹 **لبدء الاستخدام، استخدم الأزرار أدناه.**"
    )
    
    try:
        await client.send_message(int(user_id), welcome_msg, parse_mode='markdown')
    except:
        pass

async def create_math_verification():
    operations = ['+', '-', '*']
    op = random.choice(operations)
    if op == '+':
        a = random.randint(10, 50)
        b = random.randint(10, 50)
        answer = a + b
    elif op == '-':
        a = random.randint(20, 80)
        b = random.randint(10, a)
        answer = a - b
    else:
        a = random.randint(2, 10)
        b = random.randint(2, 10)
        answer = a * b
    
    problem = f"{a} {op} {b}"
    return problem, str(answer)

async def ask_verification(uid):
    problem, answer = await create_math_verification()
    verification_data = {
        'problem': problem,
        'answer': answer,
        'attempts': 0,
        'max_attempts': 3
    }
    return verification_data, f"**تحقق من أنك إنسان**\n\nحل المسألة التالية: `{problem}`\n\nأرسل الناتج كرقم فقط."

def mark_user_verified(uid):
    uid_str = str(uid)
    verified_users[uid_str] = True
    save(VERIFIED_USERS_FILE, verified_users)
    
    if uid_str in syyad_users:
        syyad_users[uid_str]['verified'] = True
        save(USER_FILE, syyad_users)

def is_user_verified(uid):
    uid_str = str(uid)
    return verified_users.get(uid_str, False) or syyad_users.get(uid_str, {}).get('verified', False)

async def check_force_subscription(user_id):
    if not force_sub_channels or not syyad_conf.get('force_sub_enabled', True):
        return True
    
    user_id = int(user_id)
    
    for key, channel_data in force_sub_channels.items():
        try:
            channel_id = channel_data['channel_id']
            channel_entity = await client.get_entity(channel_id)
            
            try:
                participant = await client.get_participants(channel_entity, limit=1)
                user_found = False
                
                async for member in client.iter_participants(channel_entity, limit=100):
                    if member.id == user_id:
                        user_found = True
                        break
                
                if not user_found:
                    print(f"❌ المستخدم {user_id} غير مشترك في قناة {channel_data['channel_name']}")
                    return False
                    
            except Exception as e:
                print(f"⚠️ خطأ في التحقق من القناة {channel_data['channel_name']}: {e}")
                try:
                    participants = await client.get_participants(channel_entity, limit=200)
                    user_ids = [p.id for p in participants]
                    if user_id not in user_ids:
                        return False
                except:
                    print(f"⚠️ تعذر التحقق من القناة {channel_data['channel_name']}، يتم التجاهل")
                    continue
                    
        except Exception as e:
            print(f"❌ خطأ في التحقق من القناة {key}: {e}")
            continue
    
    return True

async def send_force_sub_message(uid):
    if not force_sub_channels or not syyad_conf.get('force_sub_enabled', True):
        return
    
    message = "**⚠️ لا يمكنك استخدام البوت!**\n\n"
    message += "**يجب الاشتراك في القنوات التالية أولاً:**\n\n"
    
    buttons = []
    channel_buttons = []
    
    for idx, channel_data in enumerate(force_sub_channels.values(), 1):
        channel_link = channel_data.get('channel_link', channel_data['channel_id'])
        message += f"{idx}. {channel_data['channel_name']}\n"
        channel_buttons.append(Button.url(f"📢 القناة {idx}", channel_link))
    
    if len(channel_buttons) > 0:
        row1 = channel_buttons[:3]
        row2 = channel_buttons[3:6]
        if row1:
            buttons.append(row1)
        if row2:
            buttons.append(row2)
    
    buttons.append([Button.inline("🔄 تحقق من الاشتراك", data="check_subscription")])
    buttons.append([Button.inline("❌ إلغاء", data="cancel_op")])
    
    try:
        await client.send_message(int(uid), message, parse_mode='markdown', buttons=buttons)
    except Exception as e:
        print(f"❌ فشل إرسال رسالة الاشتراك الإجباري للمستخدم {uid}: {e}")

async def init_acc(phone, api_id, api_hash, sess_str):
    if phone in u_clients and u_clients[phone].is_connected():
        return

    u_client = TelegramClient(StringSession(sess_str), api_id, api_hash)

    @u_client.on(events.NewMessage(incoming=True, chats=777000))
    async def proc_code_msg(event):
        global code_reqs
        code_match = re.search(r'Login code: (\d+)', event.message.text)
        if not code_match:
            code_match = re.search(r'\b(\d{5,})\b', event.message.text)

        if code_match:
            code = code_match.group(1)
            buyer_id = code_reqs.get(phone)

            if buyer_id:
                await client.send_message(
                    int(buyer_id),
                    f"**تم استلام الكود بنجاح**\n\n"
                    f"الرقم: `{phone}`\n"
                    f"الكود: `{code}`"
                )
                acc_details = u_sessions.get(phone, {})
                two_fa_pass = acc_details.get('two_factor_password', 'لا يوجد')
                if two_fa_pass and two_fa_pass != "لا يوجد":
                    await client.send_message(
                        int(buyer_id),
                        f"كلمة مرور التحقق بخطوتين: `{two_fa_pass}`"
                    )

                if phone in code_reqs:
                    del code_reqs[phone]
            raise events.StopPropagation

    try:
        await u_client.connect()
        if not await u_client.is_user_authorized():
            if phone in u_clients:
                del u_clients[phone]
            return
        u_clients[phone] = u_client
    except Exception:
        if phone in u_clients:
            del u_clients[phone]

async def run_accs():
    for phone, details in u_sessions.items():
        api_id = details.get('api_id')
        api_hash = details.get('api_hash')
        sess_str = details.get('session_str')
        if api_id and api_hash and sess_str:
            asyncio.create_task(init_acc(phone, api_id, api_hash, sess_str))

async def edit_post(phone):
    if syyad_conf.get('publish_channel_id') and phone in avail_nums:
        num_details = avail_nums[phone]
        msg_id = num_details.get('publish_message_id')
        if msg_id:
            try:
                orig_msg = await client.get_messages(syyad_conf['publish_channel_id'], ids=msg_id)
                if orig_msg:
                    new_text = f"#تم_البيع\n\n{orig_msg.text}"
                    await client.edit_message(syyad_conf['publish_channel_id'], msg_id, new_text)
            except Exception:
                pass

async def add_num(event):
    async with client.conversation(event.sender_id, timeout=600) as conv:
        await conv.send_message("أرسل الرقم الذي تريد إضافته (مع رمز الدولة +):", buttons=[[Button.inline("إلغاء", data='cancel_op')]])
        phone_resp = await conv.get_response()

        if phone_resp.text == 'إلغاء':
             await conv.send_message("تم الإلغاء.", buttons=[[Button.inline("العودة للقائمة الرئيسية", data='main_admin_menu')]])
             return None, None

        phone = phone_resp.text.strip()

        if not phone.startswith('+') or not phone[1:].isdigit():
            await conv.send_message("رقم الهاتف غير صالح.", buttons=[[Button.inline("العودة للقائمة الرئيسية", data='main_admin_menu')]])
            return None, None

        if phone in u_sessions:
            await conv.send_message("هذا الرقم مسجل بالفعل.", buttons=[[Button.inline("العودة للقائمة الرئيسية", data='main_admin_menu')]])
            return None, None

        new_client = None
        try:
            new_client = TelegramClient(StringSession(), REG_ID, REG_HASH)
            await new_client.connect()

            two_fa_pass = "لا يوجد"
            code_req_info = await new_client.send_code_request(phone)
            await conv.send_message("تم إرسال الكود إلى الرقم، يرجى إرسال الكود المستلم:", buttons=[[Button.inline("إلغاء", data='cancel_op')]])

            code_resp = await conv.get_response()
            if code_resp.text == 'إلغاء':
                await conv.send_message("تم الإلغاء.", buttons=[[Button.inline("العودة للقائمة الرئيسية", data='main_admin_menu')]])
                return None, None

            ver_code = code_resp.text.strip()

            try:
                await new_client.sign_in(
                    phone=phone,
                    code=ver_code,
                    phone_code_hash=code_req_info.phone_code_hash
                )
            except SessionPasswordNeededError:
                await conv.send_message("الحساب محمي بكلمة مرور. يرجى إرسال كلمة المرور (التحقق بخطوتين):", buttons=[[Button.inline("إلغاء", data='cancel_op')]])

                pass_resp = await conv.get_response()
                if pass_resp.text == 'إلغاء':
                    await conv.send_message("تم الإلغاء.", buttons=[[Button.inline("العودة للقائمة الرئيسية", data='main_admin_menu')]])
                    return None, None

                two_fa_pass = pass_resp.text.strip()
                await new_client.sign_in(password=two_fa_pass)

            sess_str = new_client.session.save()
            new_acc_details = {
                'api_id': REG_ID,
                'api_hash': REG_HASH,
                'session_str': sess_str,
                'two_factor_password': two_fa_pass
            }

            await conv.send_message("تم تسجيل الحساب بنجاح. الآن، أدخل تفاصيل البيع.")

            await conv.send_message("أرسل سعر الرقم بالنقاط (0 إذا لم يكن بالنقاط):", buttons=[[Button.inline("إلغاء", data='cancel_op')]])
            pts_price_resp = await conv.get_response()
            if pts_price_resp.text == 'إلغاء':
                await conv.send_message("تم الإلغاء.", buttons=[[Button.inline("العودة للقائمة الرئيسية", data='main_admin_menu')]])
                return None, None
            try:
                pts_price = int(pts_price_resp.text.strip())
            except ValueError:
                await conv.send_message("السعر بالنقاط غير صالح.", buttons=[[Button.inline("العودة للقائمة الرئيسية", data='main_admin_menu')]])
                return None, None

            await conv.send_message("أرسل سعر الرقم بالنجوم (0 إذا لم يكن بالنجوم):", buttons=[[Button.inline("إلغاء", data='cancel_op')]])
            star_price_resp = await conv.get_response()
            if star_price_resp.text == 'إلغاء':
                await conv.send_message("تم الإلغاء.", buttons=[[Button.inline("العودة للقائمة الرئيسية", data='main_admin_menu')]])
                return None, None
            try:
                star_price = int(star_price_resp.text.strip())
            except ValueError:
                await conv.send_message("السعر بالنجوم غير صالح.", buttons=[[Button.inline("العودة للقائمة الرئيسية", data='main_admin_menu')]])
                return None, None

            await conv.send_message("أرسل اسم الدولة:", buttons=[[Button.inline("إلغاء", data='cancel_op')]])
            ctry_resp = await conv.get_response()
            if ctry_resp.text == 'إلغاء':
                await conv.send_message("تم الإلغاء.", buttons=[[Button.inline("العودة للقائمة الرئيسية", data='main_admin_menu')]])
                return None, None
            ctry_name = ctry_resp.text.strip()

            sale_info = {
                "price_points": pts_price,
                "price_stars": star_price,
                "country": ctry_name,
                "status": "available",
                "added_by": str(event.sender_id),
                "buyer_id": None,
                "booked_by": None,
                "booking_time": None,
                "expiry_time": None,
                "deposit_paid_stars": None,
                "publish_message_id": None
            }
           #Kasper ali @lll6r 
            if syyad_conf.get('publish_channel_id'):
                pub_text = (
                    f"**رقم جديد متاح للبيع**\n\n"
                    f"📞 **الرقم:** `{mask_phone_number(phone)}`\n"
                    f"🌍 **الدولة:** {ctry_name}\n"
                )
                if pts_price > 0:
                    pub_text += f"💰 **السعر بالنقاط:** {pts_price}\n"
                if star_price > 0:
                    pub_text += f"🌟 **السعر بالنجوم:** {star_price}\n"
#Kasper ali @lll6r 
                try:
                    sent_msg = await client.send_message(
                        syyad_conf['publish_channel_id'],
                        pub_text,
                        parse_mode='markdown'
                    )
                    sale_info["publish_message_id"] = sent_msg.id
                except Exception as e:
                     await conv.send_message(f"لم يتمكن من النشر في القناة: {e}")
#Kasper ali @lll6r 
#Kasper ali @lll6r 
            await conv.send_message(
                f"تمت إضافة الرقم `{mask_phone_number(phone)}` بنجاح وعرضه للبيع.",
                parse_mode='markdown',
                buttons=[[Button.inline("العودة للقائمة الرئيسية", data='main_admin_menu')]]
            )
#Kasper ali @lll6r 
            return {phone: new_acc_details}, {phone: sale_info}

        except FloodWaitError as e:
            await conv.send_message(f"حدث خطأ فيضان. يرجى الانتظار {e.seconds} ثانية.", buttons=[[Button.inline("العودة للقائمة الرئيسية", data='main_admin_menu')]])
            return None, None
        except Exception as e:
            await conv.send_message(f"حدث خطأ: {str(e)}", buttons=[[Button.inline("العودة للقائمة الرئيسية", data='main_admin_menu')]])
            return None, None
        finally:
            if new_client and new_client.is_connected():
                await new_client.disconnect()
#Kasper @lll6r 
async def show_a_nums(event):
    if not avail_nums:
        await event.edit("لا توجد أرقام مضافة حالياً.", buttons=[[Button.inline("العودة لقسم الأرقام", data="admin_numbers_section")]])
        return
#tlegram @lll6r 
    lines = []
    buttons = []

    for phone, details in avail_nums.items():
        status = details.get('status', 'N/A')
        emoji = ""
        txt = ""
#حقوق كاسبر علي @lll6r
        if status == 'available':
            emoji = "🟢"
            txt = "متاح"
        elif status == 'booked':
            emoji = "🟡"
            booked_by = details.get('booked_by', 'N/A')
            expiry = details.get('expiry_time')
            if expiry:
                rem_sec = max(0, int(expiry - time.time()))
                mins = rem_sec // 60
                secs = rem_sec % 60
                txt = f"محجوز لـ `{booked_by}` ({mins:02d}:{secs:02d} متبقي)"
            else:
                txt = f"محجوز لـ `{booked_by}`"
        elif status == 'sold':
            emoji = "🔴"
            txt = f"مباع للمستخدم `{details.get('buyer_id', 'غير معروف')}`"

        lines.append(
            f"📞 الرقم: `{mask_phone_number(phone)}`\n"
            f"🌍 الدولة: {details.get('country', 'N/A')}\n"
            f"💰 السعر (نقاط): {details.get('price_points', 0)}\n"
            f"🌟 السعر (نجوم): {details.get('price_stars', 0)}\n"
            f"{emoji} الحالة: {txt}\n"
            f"--------------------"
        )
        buttons.append([Button.inline(f"{mask_phone_number(phone)} ({txt})", data=f"view_specific_number:{phone}")])

    msg = "**قائمة الأرقام المضافة:**\n\n" + "\n".join(lines)

    buttons.append([Button.inline("العودة لقسم الأرقام", data="admin_numbers_section")])
    await event.edit(msg, buttons=buttons, parse_mode='markdown')

async def show_a_del(event):
    if not avail_nums:
        await event.edit("لا توجد أرقام لحذفها حالياً.", buttons=[[Button.inline("العودة لقسم الأرقام", data="admin_numbers_section")]])
        return

    buttons = []
    for phone in avail_nums:
        buttons.append([Button.inline(f"❌ حذف الرقم {mask_phone_number(phone)}", data=f"delete_number_confirm:{phone}")])

    buttons.append([Button.inline("العودة لقسم الأرقام", data="admin_numbers_section")])
    await event.edit("اختر الرقم الذي تريد حذفه:", buttons=buttons)

async def show_a_list(event):
    adm_list = "\n".join([f"- `{adm_id}`" for adm_id in syyad_conf['admin_ids']]) if syyad_conf['admin_ids'] else "لا يوجد أدمنية حالياً."
    await event.edit(
        f"**قائمة الأدمنية:**\n{adm_list}",
        buttons=[[Button.inline("العودة لقسم الأدمنية", data="admin_admins_section")]],
        parse_mode='markdown'
    )
#Kasper ali @lll6r 
async def show_a_rates(event):
    lines = []
    buttons = []
    if syyad_conf['chargeRates']:
        for idx, rate in enumerate(syyad_conf['chargeRates']):
            lines.append(f"- {rate['points']} نقاط مقابل {rate['stars']} نجوم")
            buttons.append([Button.inline(f"🗑️ حذف {rate['points']} نقاط بـ {rate['stars']} نجوم", data=f"delete_charge_rate:{idx}")])
    else:
        lines.append("لا توجد تسعيرات شحن معرفة حالياً.")

    msg = "**تسعيرات شحن النجوم إلى نقاط:**\n\n" + "\n".join(lines)
    buttons.insert(0, [Button.inline("➕ إضافة تسعيرة شحن", data="add_charge_rate")])
    buttons.append([Button.inline("العودة لقسم الإعدادات", data="admin_settings_section")])
    await event.edit(msg, buttons=buttons, parse_mode='markdown')

async def show_user_numbers_menu(event, uid):
    user_data = get_syyad_bal(uid)
    old_nums = user_data.get('old_numbers', [])
    new_nums = user_data.get('new_numbers', [])
    
    msg = "**🔢 أرقامي**\n\n"
    
    if not old_nums and not new_nums:
        msg += "لا توجد أرقام في حسابك حالياً."
        buttons = [[Button.inline("العودة للقائمة الرئيسية", data="user_main_menu")]]
    else:
        buttons = []
        
        if old_nums:
            msg += "**📱 الأرقام القديمة:**\n"
            for i, phone in enumerate(old_nums, 1):
                msg += f"{i}. `{phone}`\n"
            buttons.append([Button.inline("📋 عرض الأرقام القديمة", data="user_show_old_numbers")])
            
        if new_nums:
            msg += "\n**🆕 الأرقام الجديدة:**\n"
            for i, phone in enumerate(new_nums, 1):
                msg += f"{i}. `{phone}`\n"
            buttons.append([Button.inline("📋 عرض الأرقام الجديدة", data="user_show_new_numbers")])
        
        buttons.append([Button.inline("العودة للقائمة الرئيسية", data="user_main_menu")])
    #حقوق كاسبر علي @lll6r
    await event.edit(msg, parse_mode='markdown', buttons=buttons)

async def show_user_numbers_list(event, uid, num_type):
    user_data = get_syyad_bal(uid)
    
    if num_type == "old":
        numbers = user_data.get('old_numbers', [])
        title = "الأرقام القديمة"
    else:
        numbers = user_data.get('new_numbers', [])
        title = "الأرقام الجديدة"
    
    if not numbers:
        await event.edit(f"لا توجد {title} في حسابك.", buttons=[[Button.inline("العودة لأرقامي", data="user_my_numbers")]])
        return
    #Kasper ali @lll6r 
    msg = f"**{title}:**\n\n"
    for i, phone in enumerate(numbers, 1):
        msg += f"{i}. `{phone}`\n"
    
    buttons = [[Button.inline("العودة لأرقامي", data="user_my_numbers")]]
    await event.edit(msg, parse_mode='markdown', buttons=buttons)

async def calculate_daily_ranking():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    ranking_data = []
    
    for uid, user_data in syyad_users.items():
        ranking_score = (
            user_data.get('points', 0) +
            (user_data.get('stars', 0) * 10) +
            (user_data.get('referral_count', 0) * 50) +
            (len(user_data.get('old_numbers', [])) * 100) +
            (len(user_data.get('new_numbers', [])) * 200)
        )
        ranking_data.append((uid, ranking_score))
    #حقوق كاسبر علي @lll6r
    ranking_data.sort(key=lambda x: x[1], reverse=True)
    
    for rank, (uid, score) in enumerate(ranking_data, 1):
        syyad_users[uid]['daily_ranking'] = rank
    
    save(USER_FILE, syyad_users)
    return ranking_data[:10]

async def show_top_users(event):
    top_users = await calculate_daily_ranking()
    
    msg = "🏆 **أفضل 10 مستخدمين اليوم** 🏆\n\n"
    
    emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    for i, (uid, score) in enumerate(top_users[:10]):
        try:
            user_entity = await client.get_entity(int(uid))
            username = f"@{user_entity.username}" if user_entity.username else user_entity.first_name or f"المستخدم {uid}"
        except:
            username = f"المستخدم {uid}"
        #Kasper ali @lll6r 
        user_data = get_syyad_bal(uid)
        msg += f"{emojis[i]} {username}\n"
        msg += f"   النقاط: {user_data['points']} | النجوم: {user_data['stars']}\n"
        msg += f"   عدد الإحالات: {user_data['referral_count']}\n\n"
    
    buttons = [[Button.inline("العودة للقائمة الرئيسية", data="user_main_menu")]]
    await event.edit(msg, buttons=buttons)

async def show_u_main(event):
    send_func = event.respond if isinstance(event, events.NewMessage.Event) else event.edit
    uid = str(event.sender_id)
    
    if syyad_conf.get('force_sub_enabled', True) and force_sub_channels:
        is_subscribed = await check_force_subscription(uid)
        if not is_subscribed:
            await event.answer("❌ يجب الاشتراك في القنوات أولاً!", alert=True)
            await send_force_sub_message(uid)
            return
    #حقوق كاسبر علي @lll6r
    user_bal = get_syyad_bal(uid)
    
    points_button = [Button.inline(f"💰 نقاطي: {user_bal['points']}", data="user_show_points")]
    top_users_button = [Button.inline("🏆 أفضل 10 مستخدمين", data="show_top_users")]
    
    main_buttons = [
        points_button,
        [
            Button.inline('🛒 شراء رقم', 'user_buy_number_menu'),
            Button.inline('💰 شحن نقاط', 'user_charge_points_menu')
        ],
        [
            Button.inline('🎁 الهدية اليومية', 'user_daily_gift'),
            Button.inline('🔢 أرقامي', 'user_my_numbers')
        ],
        top_users_button
    ]
    
    await send_func(
        f'**أهلاً بك في بوت شراء الأرقام**\n\n'
        f'💰 **رصيد النقاط:** `{user_bal["points"]}`\n'
        f'🌟 **رصيد النجوم:** `{user_bal["stars"]}`\n'
        f'📊 **عدد الإحالات:** `{user_bal["referral_count"]}`\n'
        f'🏅 **ترتيبك اليومي:** `#{user_bal["daily_ranking"]}`',
        parse_mode='markdown',
        buttons=main_buttons
    )

async def show_u_points(event, uid):
    if syyad_conf.get('force_sub_enabled', True) and force_sub_channels:
        is_subscribed = await check_force_subscription(uid)
        if not is_subscribed:
            await event.answer("❌ يجب الاشتراك في القنوات أولاً!", alert=True)
            await send_force_sub_message(uid)
            return
    
    user_bal = get_syyad_bal(uid)
    
    msg = (
        f"**💎 تفاصيل نقاطك**\n\n"
        f"💰 **رصيد النقاط:** `{user_bal['points']}`\n"
        f"🌟 **رصيد النجوم:** `{user_bal['stars']}`\n"
        f"📊 **عدد الإحالات:** `{user_bal['referral_count']}`\n"
        f"💵 **مجموع الأرباح من الإحالات:** `{user_bal.get('total_earned_from_referrals', 0)}` نقطة\n"
        f"🏅 **ترتيبك اليومي:** `#{user_bal['daily_ranking']}`\n"
        f"📱 **عدد أرقامك:** `{len(user_bal.get('old_numbers', [])) + len(user_bal.get('new_numbers', []))}`\n\n"
        f"**🎯 طرق زيادة نقاطك:**\n"
        f"1. شراء أرقام (تحصل على نقاط مقابل النجوم)\n"
        f"2. الإحالة (لكل مستخدم جديد عبر رابطك)\n"
        f"3. الهدية اليومية\n"
        f"4. الشحن بالنجوم\n"
        f"5. روابط النقاط (اطلبها من الأدمن)"
    )
    
    buttons = [
        [Button.inline("🎁 الهدية اليومية", data="user_daily_gift")],
        [Button.inline("🔗 رابط الإحالة", data="user_get_referral_link")],
        [Button.inline("العودة", data="user_main_menu")]
    ]
    
    await event.edit(msg, parse_mode='markdown', buttons=buttons)

async def show_u_ctry(event):
    uid = str(event.sender_id)
    if syyad_conf.get('force_sub_enabled', True) and force_sub_channels:
        is_subscribed = await check_force_subscription(uid)
        if not is_subscribed:
            await event.answer("❌ يجب الاشتراك في القنوات أولاً!", alert=True)
            await send_force_sub_message(uid)
            return
    
    countries = sorted(list(set(
        details['country'] for details in avail_nums.values() 
        if details.get('status') in ['available', 'booked']
    )))
    
    if not countries:
        await event.edit("لا توجد أرقام متاحة للبيع حالياً.", buttons=[[Button.inline("العودة للقائمة الرئيسية", data="user_main_menu")]])
        return
        
    buttons = []
    row = []
    for ctry in countries:
        row.append(Button.inline(ctry, data=f"show_country_numbers:{ctry}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([Button.inline("العودة للقائمة الرئيسية", data="user_main_menu")])
    await event.edit("اختر الدولة التي تريد شراء رقم منها:", buttons=buttons)

async def show_u_nums(event, ctry):
    uid = str(event.sender_id)
    if syyad_conf.get('force_sub_enabled', True) and force_sub_channels:
        is_subscribed = await check_force_subscription(uid)
        if not is_subscribed:
            await event.answer("❌ يجب الاشتراك في القنوات أولاً!", alert=True)
            await send_force_sub_message(uid)
            return
    
    nums_in_ctry = {
        phone: details for phone, details in avail_nums.items()
        if details.get('country') == ctry and details.get('status') in ['available', 'booked']
    }
    user_id = str(event.sender_id)

    avail_list = [num for num, details in nums_in_ctry.items() if details.get('status') == 'available']
    user_booked = [num for num, details in nums_in_ctry.items() if details.get('status') == 'booked' and str(details.get('booked_by')) == user_id]
    
    buttons = []

    if user_booked:
        for phone in user_booked:
            details = nums_in_ctry[phone]
            expiry = details.get('expiry_time')
            rem_sec = max(0, int(expiry - time.time()))
            mins, secs = divmod(rem_sec, 60)
            btn_txt = f"🔔 محجوز: {mask_phone_number(phone)} ({mins:02d}:{secs:02d} متبقي)"
            buttons.append([Button.inline(btn_txt, data=f"view_number_details:{phone}")])
    
    if avail_list:
        for phone in avail_list:
            buttons.append([Button.inline(f"📞 {mask_phone_number(phone)}", data=f"view_number_details:{phone}")])

    if not buttons:
        await event.edit(f"لا توجد أرقام متاحة حالياً في {ctry}.", buttons=[[Button.inline("العودة لاختيار الدولة", data="user_buy_number_menu")]])
        return

    buttons.append([Button.inline("العودة لاختيار الدولة", data="user_buy_number_menu")])
    await event.edit(f"الأرقام المتاحة في {ctry}:", buttons=buttons)

async def show_u_chrg(event):
    uid_str = str(event.sender_id)
    if syyad_conf.get('force_sub_enabled', True) and force_sub_channels:
        is_subscribed = await check_force_subscription(uid_str)
        if not is_subscribed:
            await event.answer("❌ يجب الاشتراك في القنوات أولاً!", alert=True)
            await send_force_sub_message(uid_str)
            return
    
    uid_str = str(event.sender_id)
    user_bal = get_syyad_bal(uid_str)

    message = (
        f"**💰 رصيدك الحالي:**\n"
        f"  - نقاط: `{user_bal['points']}`\n\n"
        f"اختر طريقة شحن النقاط:"
    )

    buttons = [
        [
            Button.inline('🔗 رابط الإحالة', 'user_get_referral_link'),
            Button.inline("🌟 شحن بالنجوم", 'user_charge_by_stars_menu')
        ],
        [Button.inline("العودة للقائمة الرئيسية", data="user_main_menu")]
    ]
    await event.edit(message, parse_mode='markdown', buttons=buttons)

async def show_u_star(event):
    uid_str = str(event.sender_id)
    if syyad_conf.get('force_sub_enabled', True) and force_sub_channels:
        is_subscribed = await check_force_subscription(uid_str)
        if not is_subscribed:
            await event.answer("❌ يجب الاشتراك في القنوات أولاً!", alert=True)
            await send_force_sub_message(uid_str)
            return
    
    buttons = []
    if syyad_conf['chargeRates']:
        for idx, rate in enumerate(syyad_conf['chargeRates']):
            buttons.append([Button.inline(f"شحن {rate['points']} نقطة مقابل {rate['stars']} نجوم", data=f"charge_by_stars:{idx}")])
    else:
        await event.edit("لا توجد عروض شحن بالنجوم متاحة حالياً.", buttons=[[Button.inline("العودة", data="user_charge_points_menu")]])
        return

    buttons.append([Button.inline("العودة", data="user_charge_points_menu")])
    await event.edit("اختر باقة الشحن المناسبة:", buttons=buttons)

async def hndl_force_sub_menu(event):
    if not is_adm(event.sender_id):
        return
    
    await event.edit(
        "**⚙️ إدارة الاشتراك الإجباري**\n\n"
        "اختر الإجراء المطلوب:",
        buttons=[
            [Button.inline("➕ إضافة قناة", data="add_force_sub_channel")],
            [Button.inline("🗑️ حذف قناة", data="remove_force_sub_channel")],
            [Button.inline("📋 عرض القنوات", data="show_force_sub_channels")],
            [Button.inline("❌ تعطيل النظام", data="disable_force_sub")] if syyad_conf.get('force_sub_enabled', True) else 
            [Button.inline("✅ تفعيل النظام", data="enable_force_sub")],
            [Button.inline("العودة", data="admin_settings_section")]
        ]
    )

async def hndl_add_force_sub(event):
    async with client.conversation(event.sender_id, timeout=120) as conv:
        await conv.send_message(
            "أرسل رابط القناة أو اليوزر (@username) للاشتراك الإجباري:",
            buttons=[[Button.inline("إلغاء", data='cancel_op')]]
        )
        channel_resp = await conv.get_response()
        if channel_resp.text == 'إلغاء':
            await conv.send_message("تم الإلغاء.", buttons=[[Button.inline("العودة", data='force_sub_menu')]])
            return
        
        channel_input = channel_resp.text.strip()
        
        try:
            channel_entity = await client.get_entity(channel_input)
            channel_id = channel_entity.id
            channel_name = channel_entity.title
            
            await conv.send_message("جارٍ إضافة القناة...")
            
            channel_key = f"channel_{channel_id}"
            force_sub_channels[channel_key] = {
                'channel_id': channel_id,
                'channel_name': channel_name,
                'channel_link': f"https://t.me/{channel_entity.username}" if hasattr(channel_entity, 'username') and channel_entity.username else channel_input,
                'added_by': str(event.sender_id),
                'added_date': datetime.datetime.now().isoformat()
            }
            
            save(FORCE_SUB_FILE, force_sub_channels)
            
            await conv.send_message(
                f"✅ تمت إضافة القناة **{channel_name}** للاشتراك الإجباري بنجاح.",
                buttons=[[Button.inline("العودة", data='force_sub_menu')]]
            )
        except Exception as e:
            await conv.send_message(
                f"❌ حدث خطأ: {str(e)}\nتأكد أن البوت أدمن في القناة وأن الرابط صحيح.",
                buttons=[[Button.inline("العودة", data='force_sub_menu')]]
            )

async def hndl_remove_force_sub(event):
    if not force_sub_channels:
        await event.answer("لا توجد قنوات للاشتراك الإجباري.", alert=True)
        return
    
    buttons = []
    for key, channel_data in force_sub_channels.items():
        buttons.append([Button.inline(f"🗑️ {channel_data['channel_name']}", data=f"remove_force_sub_confirm:{key}")])
    
    buttons.append([Button.inline("العودة", data="force_sub_menu")])
    await event.edit("اختر القناة التي تريد حذفها:", buttons=buttons)

async def hndl_remove_force_sub_confirm(event, channel_key):
    if channel_key in force_sub_channels:
        channel_name = force_sub_channels[channel_key]['channel_name']
        buttons = [
            [Button.inline("✅ نعم، حذف", data=f"remove_force_sub_execute:{channel_key}")],
            [Button.inline("❌ لا، إلغاء", data="remove_force_sub_channel")]
        ]
        await event.edit(f"هل أنت متأكد من حذف قناة **{channel_name}** من الاشتراك الإجباري؟", buttons=buttons)
    else:
        await event.answer("القناة غير موجودة.", alert=True)

async def hndl_remove_force_sub_execute(event, channel_key):
    if channel_key in force_sub_channels:
        channel_name = force_sub_channels[channel_key]['channel_name']
        del force_sub_channels[channel_key]
        save(FORCE_SUB_FILE, force_sub_channels)
        await event.answer(f"تم حذف قناة {channel_name} بنجاح.", alert=True)
        await hndl_remove_force_sub(event)
    else:
        await event.answer("القناة غير موجودة.", alert=True)

async def hndl_show_force_sub_channels(event):
    if not force_sub_channels:
        await event.edit("لا توجد قنوات للاشتراك الإجباري.", buttons=[[Button.inline("العودة", data="force_sub_menu")]])
        return
    
    message = "**📢 قنوات الاشتراك الإجباري:**\n\n"
    for idx, channel_data in enumerate(force_sub_channels.values(), 1):
        message += f"{idx}. **{channel_data['channel_name']}**\n"
        message += f"   رابط: {channel_data.get('channel_link', 'غير متوفر')}\n"
        message += f"   أضيف بواسطة: `{channel_data['added_by']}`\n"
        message += f"   التاريخ: {channel_data['added_date'][:10]}\n\n"
    
    await event.edit(message, buttons=[[Button.inline("العودة", data="force_sub_menu")]])

async def hndl_toggle_force_sub(event):
    syyad_conf['force_sub_enabled'] = not syyad_conf.get('force_sub_enabled', True)
    save_all()
    
    if syyad_conf['force_sub_enabled']:
        await event.answer("✅ تم تفعيل نظام الاشتراك الإجباري.", alert=True)
    else:
        await event.answer("❌ تم تعطيل نظام الاشتراك الإجباري.", alert=True)
    
    await hndl_force_sub_menu(event)

async def hndl_broadcast_menu(event):
    if not is_adm(event.sender_id):
        return
    
    await event.edit(
        "**📢 نظام البث**\n\n"
        "اختر نوع البث:",
        buttons=[
            [Button.inline("📝 بث رسالة", data="send_broadcast_message")],
            [Button.inline("📋 الرسائل السابقة", data="show_broadcast_history")],
            [Button.inline("العودة", data="main_admin_menu")]
        ]
    )

async def hndl_send_broadcast_message(event):
    async with client.conversation(event.sender_id, timeout=300) as conv:
        await conv.send_message(
            "أرسل الرسالة التي تريد بثها:\n\n"
            "يمكنك استخدام HTML للتحكم بالتنسيق:\n"
            "<b>عريض</b>\n"
            "<i>مائل</i>\n"
            "<u>تحته خط</u>\n"
            "<code>كود</code>\n\n"
            "أرسل 'إلغاء' للإلغاء.",
            buttons=[[Button.inline("إلغاء", data='cancel_op')]]
        )
        
        message_resp = await conv.get_response()
        if message_resp.text == 'إلغاء':
            await conv.send_message("تم الإلغاء.", buttons=[[Button.inline("العودة", data='broadcast_menu')]])
            return
        
        broadcast_text = message_resp.text
        content_hash = hashlib.md5(broadcast_text.encode()).hexdigest()
        broadcast_texts[content_hash] = broadcast_text
        
        buttons = [
            [Button.inline("✅ نعم، البث الآن", data=f"confirm_broadcast:text:{content_hash}")],
            [Button.inline("❌ لا، إلغاء", data="broadcast_menu")]
        ]
        
        preview_text = broadcast_text[:200] + "..." if len(broadcast_text) > 200 else broadcast_text
        await conv.send_message(
            f"**معاينة الرسالة:**\n\n{preview_text}\n\n"
            f"سيتم إرسال هذه الرسالة إلى **{len(syyad_users)}** مستخدم.\n"
            f"هل تريد المتابعة؟",
            buttons=buttons
        )

async def hndl_confirm_broadcast(event, broadcast_type, content_hash):
    await event.edit("جارٍ إرسال البث...")
    
    success_count = 0
    fail_count = 0
    total_users = len(syyad_users)
    
    broadcast_id = f"broadcast_{int(time.time())}"
    
    broadcast_text = broadcast_texts.get(content_hash, "رسالة بث")
    
    broadcast_messages[broadcast_id] = {
        'type': broadcast_type,
        'content_hash': content_hash,
        'content': broadcast_text,
        'sent_by': str(event.sender_id),
        'sent_date': datetime.datetime.now().isoformat(),
        'total_users': total_users,
        'success_count': 0,
        'fail_count': 0
    }
    
    for user_id_str in syyad_users.keys():
        try:
            user_id = int(user_id_str)
            await client.send_message(user_id, broadcast_text, parse_mode='html')
            success_count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            fail_count += 1
            print(f"Failed to send to {user_id_str}: {e}")
    
    broadcast_messages[broadcast_id]['success_count'] = success_count
    broadcast_messages[broadcast_id]['fail_count'] = fail_count
    save(BROADCAST_FILE, broadcast_messages)
    
    if content_hash in broadcast_texts:
        del broadcast_texts[content_hash]
    
    await event.edit(
        f"✅ تم إكمال البث!\n\n"
        f"📊 **الإحصائيات:**\n"
        f"• إجمالي المستخدمين: {total_users}\n"
        f"• تم الإرسال بنجاح: {success_count}\n"
        f"• فشل الإرسال: {fail_count}\n"
        f"• نسبة النجاح: {(success_count/total_users*100):.1f}%",
        buttons=[[Button.inline("العودة", data="broadcast_menu")]]
    )

async def hndl_show_broadcast_history(event):
    if not broadcast_messages:
        await event.edit("لا توجد رسائل بث سابقة.", buttons=[[Button.inline("العودة", data="broadcast_menu")]])
        return
    
    message = "**📋 سجل البث:**\n\n"
    for bid, broadcast in list(broadcast_messages.items())[-10:]:
        message += f"📅 **{broadcast['sent_date'][:10]}**\n"
        message += f"👤 المرسل: `{broadcast['sent_by']}`\n"
        message += f"📊 النجاح: {broadcast.get('success_count', 0)}/{broadcast['total_users']}\n"
        preview = broadcast.get('content', '')[:50] + "..." if len(broadcast.get('content', '')) > 50 else broadcast.get('content', '')
        message += f"📝 المعاينة: {preview}\n"
        message += f"🆔 المعرف: `{bid[:8]}...`\n\n"
    
    await event.edit(message, buttons=[[Button.inline("العودة", data="broadcast_menu")]])

def generate_point_link(points, max_uses, creator_id):
    link_id = hashlib.md5(f"{points}_{max_uses}_{creator_id}_{time.time()}".encode()).hexdigest()[:8]
    point_links[link_id] = {
        'points': points,
        'max_uses': max_uses,
        'current_uses': 0,
        'creator_id': str(creator_id),
        'created_at': datetime.datetime.now().isoformat(),
        'used_by': [],
        'link_id': link_id
    }
    save(POINT_LINKS_FILE, point_links)
    return link_id

async def hndl_point_links_menu(event):
    if not is_adm(event.sender_id):
        return
    
    await event.edit(
        "**🔗 نظام روابط النقاط**\n\n"
        "اختر الإجراء:",
        buttons=[
            [Button.inline("➕ إنشاء رابط", data="create_point_link")],
            [Button.inline("📋 روابطي", data="my_point_links")],
            [Button.inline("📊 إحصائيات الروابط", data="point_links_stats")],
            [Button.inline("العودة", data="main_admin_menu")]
        ]
    )

async def hndl_create_point_link(event):
    async with client.conversation(event.sender_id, timeout=120) as conv:
        await conv.send_message("أرسل عدد النقاط التي سيتم منحها:", buttons=[[Button.inline("إلغاء", data='cancel_op')]])
        points_resp = await conv.get_response()
        if points_resp.text == 'إلغاء':
            await conv.send_message("تم الإلغاء.", buttons=[[Button.inline("العودة", data='point_links_menu')]])
            return
        
        try:
            points = int(points_resp.text.strip())
            if points <= 0:
                raise ValueError
        except ValueError:
            await conv.send_message("عدد نقاط غير صالح.", buttons=[[Button.inline("العودة", data='point_links_menu')]])
            return
        
        await conv.send_message("أرسل أقصى عدد استخدامات للرابط (0 = غير محدود):")
        uses_resp = await conv.get_response()
        try:
            max_uses = int(uses_resp.text.strip())
            if max_uses < 0:
                raise ValueError
        except ValueError:
            await conv.send_message("عدد استخدامات غير صالح.", buttons=[[Button.inline("العودة", data='point_links_menu')]])
            return
        
        link_id = generate_point_link(points, max_uses, event.sender_id)
        bot_info = await client.get_me()
        bot_username = bot_info.username
        point_link = f"https://t.me/{bot_username}?start=point_{link_id}"
        
        await conv.send_message(
            f"✅ **تم إنشاء رابط النقاط بنجاح!**\n\n"
            f"🔗 **الرابط:** `{point_link}`\n"
            f"💰 **النقاط:** `{points}` لكل مستخدم\n"
            f"👥 **الاستخدامات:** `{'غير محدود' if max_uses == 0 else max_uses}`\n"
            f"🆔 **معرف الرابط:** `{link_id}`\n\n"
            f"شارك هذا الرابط مع الآخرين!",
            buttons=[[Button.inline("العودة", data="point_links_menu")]]
        )

async def hndl_my_point_links(event):
    my_links = {k: v for k, v in point_links.items() if v['creator_id'] == str(event.sender_id)}
    
    if not my_links:
        await event.edit("ليس لديك أي روابط نقاط.", buttons=[[Button.inline("العودة", data="point_links_menu")]])
        return
    
    message = "**🔗 روابط النقاط الخاصة بك:**\n\n"
    for link_id, link_data in list(my_links.items())[-5:]:
        bot_info = await client.get_me()
        bot_username = bot_info.username
        point_link = f"https://t.me/{bot_username}?start=point_{link_id}"
        
        message += f"🆔 **{link_id}**\n"
        message += f"💰 النقاط: `{link_data['points']}`\n"
        message += f"👥 الاستخدامات: `{link_data['current_uses']}/{'∞' if link_data['max_uses'] == 0 else link_data['max_uses']}`\n"
        message += f"📅 الإنشاء: {link_data['created_at'][:10]}\n"
        message += f"🔗 الرابط: `{point_link[:30]}...`\n\n"
    
    await event.edit(message, buttons=[[Button.inline("العودة", data="point_links_menu")]])

async def hndl_point_links_stats(event):
    total_links = len(point_links)
    total_points_distributed = sum(link['points'] * link['current_uses'] for link in point_links.values())
    total_uses = sum(link['current_uses'] for link in point_links.values())
    
    top_links = sorted(point_links.items(), key=lambda x: x[1]['current_uses'], reverse=True)[:3]
    
    message = (
        f"📊 **إحصائيات روابط النقاط**\n\n"
        f"🔗 **إجمالي الروابط:** `{total_links}`\n"
        f"💰 **إجمالي النقاط الموزعة:** `{total_points_distributed}`\n"
        f"👥 **إجمالي الاستخدامات:** `{total_uses}`\n\n"
        f"🏆 **أفضل 3 روابط:**\n"
    )
    
    for i, (link_id, link_data) in enumerate(top_links, 1):
        message += f"{i}. **{link_id}** - {link_data['current_uses']} استخدام ({link_data['points']} نقطة لكل استخدام)\n"
    
    await event.edit(message, buttons=[[Button.inline("العودة", data="point_links_menu")]])

def run_poll():
    bot.polling(none_stop=True)

async def run_timer(phone, uid, expiry):
    global avail_nums, res_timers

    rem_time = expiry - time.time()
    if rem_time <= 0:
        await end_resv(phone, notify=False)
        return

    task = asyncio.create_task(asyncio.sleep(rem_time))
    res_timers[phone] = task

    try:
        await task
        await end_resv(phone)
    except asyncio.CancelledError:
        pass
    finally:
        if phone in res_timers:
            del res_timers[phone]

async def end_resv(phone, notify=True):
    global avail_nums
    if phone in avail_nums and avail_nums[phone]['status'] == 'booked':
        booked_by = avail_nums[phone]['booked_by']
        avail_nums[phone].update({
            'status': 'available',
            'booked_by': None,
            'booking_time': None,
            'expiry_time': None,
            'deposit_paid_stars': None
        })
        save_all()

        if notify and booked_by:
            await client.send_message(
                int(booked_by),
                f"🚨 **انتهى حجز الرقم `{mask_phone_number(phone)}`.**\n\n"
                f"لم يتم إتمام عملية الشراء في الوقت المحدد. الرقم متاح الآن للبيع مرة أخرى.",
                parse_mode='markdown'
            )

        await client.send_message(
            int(syyad_conf['admin_ids'][0]),
            f"🚨 **انتهى حجز الرقم `{phone}`.**\n"
            f"كان محجوزاً بواسطة `{booked_by}` ولم يتم إتمام الشراء.",
            parse_mode='markdown'
        )

    if phone in res_timers:
        res_timers[phone].cancel()
        del res_timers[phone]

async def init_resv():
    for phone, details in list(avail_nums.items()):
        if details.get('status') == 'booked' and details.get('expiry_time'):
            expiry = details['expiry_time']
            if expiry > time.time():
                asyncio.create_task(run_timer(phone, details['booked_by'], expiry))
            else:
                await end_resv(phone, notify=False)

async def hndl_a_main(event):
    send_func = event.respond if isinstance(event, events.NewMessage.Event) else event.edit
    await send_func(
        '**أهلاً بك في لوحة تحكم الأدمن**', parse_mode='markdown',
        buttons=[
            [
                Button.inline('قسم الأرقام', 'admin_numbers_section'),
                Button.inline('قسم الأدمنية', 'admin_admins_section')
            ],
            [
                Button.inline('قسم البيع والشراء', 'admin_sales_section'),
                Button.inline('قسم الرصيد', 'admin_balance_section')
            ],
            [
                Button.inline('الإعدادات', 'admin_settings_section'),
                Button.inline('📊 الإحصائيات', 'admin_stats')
            ],
            [
                Button.inline('📢 البث', 'broadcast_menu'),
                Button.inline('🔗 روابط النقاط', 'point_links_menu')
            ],
            [
                Button.inline('👥 سجل المستخدمين', 'admin_user_log')
            ]
        ]
    )

async def hndl_user_login_log(event):
    if not is_adm(event.sender_id):
        return
    
    total_users = len(user_login_log)
    recent_logins = []
    
    all_logins = []
    for uid, log_list in user_login_log.items():
        for log in log_list[-1:]:
            all_logins.append((log['login_time'], uid, log))
    
    all_logins.sort(key=lambda x: x[0], reverse=True)
    recent_logins = all_logins[:10]
    
    message = "**📊 سجل دخول المستخدمين**\n\n"
    message += f"👥 **إجمالي المستخدمين المسجلين:** `{total_users}`\n\n"
    message += "**🕐 آخر 10 تسجيلات دخول:**\n"
    
    for login_time, uid, log in recent_logins:
        message += f"• `{uid}` - {log.get('full_name', 'مجهول')}\n"
        message += f"  🕐 {login_time}\n"
        message += f"  📛 @{log.get('username', 'لا يوجد')}\n\n"
    
    buttons = [
        [Button.inline("📋 عرض جميع المستخدمين", data="show_all_users")],
        [Button.inline("العودة", data="main_admin_menu")]
    ]
    
    await event.edit(message, parse_mode='markdown', buttons=buttons)

async def hndl_show_all_users(event):
    if not is_adm(event.sender_id):
        return
    
    message = "**👥 قائمة جميع المستخدمين**\n\n"
    
    users_list = []
    for uid in syyad_users.keys():
        user_data = syyad_users[uid]
        user_info = await get_user_info(uid)
        name = user_info.get('first_name', f'مستخدم {uid}')
        username = f"@{user_info.get('username')}" if user_info.get('username') else 'لا يوجد'
        users_list.append((uid, name, username, user_data.get('points', 0)))
    
    users_list.sort(key=lambda x: x[3], reverse=True)
    
    for i, (uid, name, username, points) in enumerate(users_list[:20], 1):
        message += f"{i}. **{name}**\n"
        message += f"   🆔 `{uid}`\n"
        message += f"   📛 {username}\n"
        message += f"   💰 {points} نقطة\n\n"
    
    if len(users_list) > 20:
        message += f"\n... وعرض {len(users_list) - 20} مستخدم آخر"
    
    buttons = [[Button.inline("العودة", data="admin_stats")]]
    await event.edit(message, parse_mode='markdown', buttons=buttons)

async def hndl_a_stats(event):
    total_users = len(syyad_users)
    total_numbers = len(avail_nums)
    sold_numbers = len([n for n in avail_nums.values() if n.get('status') == 'sold'])
    available_numbers = len([n for n in avail_nums.values() if n.get('status') == 'available'])
    booked_numbers = len([n for n in avail_nums.values() if n.get('status') == 'booked'])
    
    total_points = sum(user.get('points', 0) for user in syyad_users.values())
    total_stars = sum(user.get('stars', 0) for user in syyad_users.values())
    total_referrals = sum(user.get('referral_count', 0) for user in syyad_users.values())
    
    top_users = sorted(syyad_users.items(), key=lambda x: x[1].get('points', 0), reverse=True)[:3]
    
    stats_msg = (
        f"📊 **إحصائيات البوت**\n\n"
        f"👥 **إجمالي المستخدمين:** `{total_users}`\n"
        f"📞 **إجمالي الأرقام:** `{total_numbers}`\n"
        f"🟢 **متاحة:** `{available_numbers}`\n"
        f"🟡 **محجوزة:** `{booked_numbers}`\n"
        f"🔴 **مبيعة:** `{sold_numbers}`\n\n"
        f"💰 **إجمالي النقاط:** `{total_points}`\n"
        f"🌟 **إجمالي النجوم:** `{total_stars}`\n"
        f"🔗 **إجمالي الإحالات:** `{total_referrals}`\n\n"
        f"🏆 **أفضل 3 مستخدمين:**\n"
    )
    
    for i, (uid, user_data) in enumerate(top_users, 1):
        stats_msg += f"{i}. `{uid}` - {user_data.get('points', 0)} نقطة\n"
    
    buttons = [[Button.inline("العودة", data="main_admin_menu")]]
    await event.edit(stats_msg, parse_mode='markdown', buttons=buttons)

async def hndl_a_nums(event):
    await event.edit(
        '**إدارة الأرقام**', parse_mode='markdown',
        buttons=[
            [
                Button.inline('➕ إضافة رقم جديد للبيع', 'add_new_number'),
                Button.inline('📋 عرض الأرقام المضافة', 'view_added_numbers')
            ],
            [
                Button.inline('🗑️ حذف الأرقام المعروضة', 'delete_displayed_numbers')
            ],
            [
                Button.inline('العودة', 'main_admin_menu')
            ]
        ]
    )

async def hndl_a_add(event):
    await event.edit('جارٍ بدء عملية إضافة الرقم...')
    new_acc, sale_details = await add_num(event)
    if new_acc and sale_details:
        u_sessions.update(new_acc)
        avail_nums.update(sale_details)
        save_all()
        for phone, info in new_acc.items():
            asyncio.create_task(init_acc(phone, info['api_id'], info['api_hash'], info['session_str']))
    else:
        await event.edit('تم إلغاء عملية إضافة الرقم أو فشلت.', buttons=[[Button.inline("العودة", data='admin_numbers_section')]])

async def hndl_a_view_num(event, phone):
    if phone in avail_nums:
        details = avail_nums[phone]
        status = details.get('status', 'N/A')
        emoji = ""
        txt = ""

        if status == 'available':
            emoji = "🟢"
            txt = "متاح"
        elif status == 'booked':
            emoji = "🟡"
            booked_by = details.get('booked_by', 'N/A')
            expiry = details.get('expiry_time')
            if expiry:
                rem_sec = max(0, int(expiry - time.time()))
                mins = rem_sec // 60
                secs = rem_sec % 60
                txt = f"محجوز لـ `{booked_by}` ({mins:02d}:{secs:02d} متبقي)"
            else:
                txt = f"محجوز لـ `{booked_by}`"
        elif status == 'sold':
            emoji = "🔴"
            txt = f"مباع للمستخدم `{details.get('buyer_id', 'غير معروف')}`"

        message = (
            f"**تفاصيل الرقم:**\n"
            f"📞 الرقم: `{phone}`\n"
            f"🌍 الدولة: {details.get('country', 'N/A')}\n"
            f"💰 السعر (نقاط): {details.get('price_points', 0)}\n"
            f"🌟 السعر (نجوم): {details.get('price_stars', 0)}\n"
            f"{emoji} الحالة: {txt}\n"
            f"بواسطة: `{details.get('added_by', 'غير معروف')}`\n"
        )
        buttons = []
        if status == 'booked':
            buttons.append([Button.inline("إلغاء الحجز", data=f"admin_cancel_booking:{phone}")])
        buttons.append([Button.inline("العودة لقائمة الأرقام", data="view_added_numbers")])

        await event.edit(message, parse_mode='markdown', buttons=buttons)

async def hndl_a_end_book(event, phone):
    if phone in avail_nums and avail_nums[phone]['status'] == 'booked':
        await end_resv(phone)
        await event.answer("تم إلغاء الحجز بنجاح.", alert=True)
        await show_a_nums(event)
    else:
        await event.answer("الحجز غير موجود أو انتهى بالفعل.", alert=True)
        await show_a_nums(event)

async def hndl_a_del_conf(event, phone):
    if phone in avail_nums:
        buttons = [
            [
                Button.inline("تأكيد الحذف", data=f"delete_number_execute:{phone}"),
                Button.inline("إلغاء", data="delete_displayed_numbers")
            ]
        ]
        await event.edit(f"هل أنت متأكد من حذف الرقم `{mask_phone_number(phone)}`؟ سيتم حذف جميع بياناته.", buttons=buttons, parse_mode='markdown')
    else:
        await event.answer("الرقم غير موجود.", alert=True)
        await show_a_del(event)

async def hndl_a_del_exec(event, phone):
    if phone in avail_nums:
        if phone in u_clients:
            await u_clients[phone].disconnect()
            del u_clients[phone]
        if phone in res_timers:
            res_timers[phone].cancel()
            del res_timers[phone]
#Kasper ali @lll6r 
        del avail_nums[phone]
        if phone in u_sessions:
            del u_sessions[phone]
        save_all()
        await event.answer(f"تم حذف الرقم `{mask_phone_number(phone)}` بنجاح.", alert=True)
        await show_a_del(event)
    else:
        await event.answer("الرقم غير موجود.", alert=True)
        await show_a_del(event)

async def hndl_a_adm_sec(event):
    await event.edit(
        '**إدارة الأدمنية**', parse_mode='markdown',
        buttons=[
            [
                Button.inline('➕ رفع أدمن', 'admin_promote_admin'),
                Button.inline('➖ تنزيل أدمن', 'admin_demote_admin')
            ],
            [
                Button.inline('📋 عرض الأدمنية', 'admin_view_admins')
            ],
            [
                Button.inline('العودة', 'main_admin_menu')
            ]
        ]
    )
#حقوق كاسبر علي @lll6r
async def hndl_a_promo(event):
    async with client.conversation(event.sender_id, timeout=120) as conv:
        await conv.send_message("أرسل آي دي المستخدم لترفعه كأدمن:", buttons=[[Button.inline("إلغاء", data='cancel_op')]])
        user_resp = await conv.get_response()
        if user_resp.text == 'إلغاء':
            await conv.send_message("تم الإلغاء.", buttons=[[Button.inline("العودة لقسم الأدمنية", data='admin_admins_section')]])
            return
        user_to_promo = user_resp.text.strip()
        if not user_to_promo.isdigit():
            await conv.send_message("آي دي غير صالح.", buttons=[[Button.inline("العودة لقسم الأدمنية", data='admin_admins_section')]])
            return
        if user_to_promo in syyad_conf['admin_ids']:
            await conv.send_message("المستخدم هو أدمن بالفعل.", buttons=[[Button.inline("العودة لقسم الأدمنية", data='admin_admins_section')]])
        else:
            syyad_conf['admin_ids'].append(user_to_promo)
            save_all()
            await conv.send_message(f"تمت ترقية المستخدم `{user_to_promo}` كأدمن.", buttons=[[Button.inline("العودة لقسم الأدمنية", data='admin_admins_section')]])

async def hndl_a_demote(event):
    async with client.conversation(event.sender_id, timeout=120) as conv:
        await conv.send_message("أرسل آي دي المستخدم لتنزيله من الأدمنية:", buttons=[[Button.inline("إلغاء", data='cancel_op')]])
        user_resp = await conv.get_response()
        if user_resp.text == 'إلغاء':
            await conv.send_message("تم الإلغاء.", buttons=[[Button.inline("العودة لقسم الأدمنية", data='admin_admins_section')]])
            return
        user_to_demote = user_resp.text.strip()
        if not user_to_demote.isdigit():
            await conv.send_message("آي دي غير صالح.", buttons=[[Button.inline("العودة لقسم الأدمنية", data='admin_admins_section')]])
            return
        if user_to_demote not in syyad_conf['admin_ids']:
            await conv.send_message("المستخدم ليس أدمن.", buttons=[[Button.inline("العودة لقسم الأدمنية", data='admin_admins_section')]])
        elif user_to_demote == str(event.sender_id):
            await conv.send_message("لا يمكنك تنزيل نفسك من الأدمنية.", buttons=[[Button.inline("العودة لقسم الأدمنية", data='admin_admins_section')]])
        else:
            syyad_conf['admin_ids'].remove(user_to_demote)
            save_all()
            await conv.send_message(f"تم تنزيل المستخدم `{user_to_demote}` من الأدمنية.", buttons=[[Button.inline("العودة لقسم الأدمنية", data='admin_admins_section')]])

async def hndl_a_sale_sec(event):
    await event.edit(
        '**إدارة البيع والشراء**', parse_mode='markdown',
        buttons=[
            [
                Button.inline('📋 عرض الأرقام المباعة', 'admin_view_sold_numbers'),
                Button.inline('📋 عرض الأرقام المتاحة', 'admin_view_available_numbers')
            ],
            [
                Button.inline('العودة', 'main_admin_menu')
            ]
        ]
    )

async def hndl_a_sold(event):
    sold_nums = [num for num, details in avail_nums.items() if details.get('status') == 'sold']
    if not sold_nums:
        await event.edit("لا توجد أرقام مباعة حالياً.", buttons=[[Button.inline("العودة لقسم البيع والشراء", data="admin_sales_section")]])
        return

    lines = []
    for phone in sold_nums:
        details = avail_nums[phone]
        lines.append(
            f"📞 الرقم: `{mask_phone_number(phone)}`\n"
            f"💰 السعر (نقاط): {details.get('price_points', 0)}\n"
            f"🌟 السعر (نجوم): {details.get('price_stars', 0)}\n"
            f"المشتري: `{details.get('buyer_id', 'غير معروف')}`\n"
            f"--------------------"
        )
    await event.edit(
        "**قائمة الأرقام المباعة:**\n\n" + "\n".join(lines),
        buttons=[[Button.inline("العودة لقسم البيع والشراء", data="admin_sales_section")]],
        parse_mode='markdown'
    )

async def hndl_a_avail(event):
    avail_filter = [num for num, details in avail_nums.items() if details.get('status') == 'available']
    if not avail_filter:
        await event.edit("لا توجد أرقام متاحة للبيع حالياً.", buttons=[[Button.inline("العودة لقسم البيع والشراء", data="admin_sales_section")]])
        return

    lines = []
    for phone in avail_filter:
        details = avail_nums[phone]
        lines.append(
            f"📞 الرقم: `{mask_phone_number(phone)}`\n"
            f"🌍 الدولة: {details.get('country', 'N/A')}\n"
            f"💰 السعر (نقاط): {details.get('price_points', 0)}\n"
            f"🌟 السعر (نجوم): {details.get('price_stars', 0)}\n"
            f"--------------------"
        )
    await event.edit(
        "**قائمة الأرقام المتاحة للبيع:**\n\n" + "\n".join(lines),
        buttons=[[Button.inline("العودة لقسم البيع والشراء", data="admin_sales_section")]],
        parse_mode='markdown'
    )

async def hndl_a_bal_sec(event):
    await event.edit(
        '**إدارة أرصدة المستخدمين**', parse_mode='markdown',
        buttons=[
            [
                Button.inline('➕ إضافة نقاط لمستخدم', 'admin_add_points'),
                Button.inline('➕ إضافة نجوم لمستخدم', 'admin_add_stars')
            ],
            [
                Button.inline('العودة', 'main_admin_menu')
            ]
        ]
    )

async def hndl_a_add_pts(event):
    async with client.conversation(event.sender_id, timeout=120) as conv:
        await conv.send_message("أرسل آي دي المستخدم لإضافة النقاط له:", buttons=[[Button.inline("إلغاء", data='cancel_op')]])
        uid_resp = await conv.get_response()
        if uid_resp.text == 'إلغاء':
            await conv.send_message("تم الإلغاء.", buttons=[[Button.inline("العودة لقسم الرصيد", data='admin_balance_section')]])
            return
        target_uid = uid_resp.text.strip()
        if not target_uid.isdigit():
            await conv.send_message("آي دي غير صالح.", buttons=[[Button.inline("العودة لقسم الرصيد", data='admin_balance_section')]])
            return

        await conv.send_message("أرسل عدد النقاط لإضافتها:", buttons=[[Button.inline("إلغاء", data='cancel_op')]])
        pts_resp = await conv.get_response()
        if pts_resp.text == 'إلغاء':
            await conv.send_message("تم الإلغاء.", buttons=[[Button.inline("العودة لقسم الرصيد", data='admin_balance_section')]])
            return
        try:
            pts_amount = int(pts_resp.text.strip())
            if pts_amount <= 0:
                raise ValueError
        except ValueError:
            await conv.send_message("عدد نقاط غير صالح.", buttons=[[Button.inline("العودة لقسم الرصيد", data='admin_balance_section')]])
            return

        user_bal = get_syyad_bal(target_uid)
        user_bal['points'] += pts_amount
        save_all()
        await conv.send_message(f"تم إضافة `{pts_amount}` نقطة للمستخدم `{target_uid}`. رصيده الحالي: `{user_bal['points']}` نقطة.", buttons=[[Button.inline("العودة لقسم الرصيد", data='admin_balance_section')]])

async def hndl_a_add_star(event):
    async with client.conversation(event.sender_id, timeout=120) as conv:
        await conv.send_message("أرسل آي دي المستخدم لإضافة النجوم له:", buttons=[[Button.inline("إلغاء", data='cancel_op')]])
        uid_resp = await conv.get_response()
        if uid_resp.text == 'إلغاء':
            await conv.send_message("تم الإلغاء.", buttons=[[Button.inline("العودة لقسم الرصيد", data='admin_balance_section')]])
            return
        target_uid = uid_resp.text.strip()
        if not target_uid.isdigit():
            await conv.send_message("آي دي غير صالح.", buttons=[[Button.inline("العودة لقسم الرصيد", data='admin_balance_section')]])
            return

        await conv.send_message("أرسل عدد النجوم لإضافتها:", buttons=[[Button.inline("إلغاء", data='cancel_op')]])
        star_resp = await conv.get_response()
        if star_resp.text == 'إلغاء':
            await conv.send_message("تم الإلغاء.", buttons=[[Button.inline("العودة لقسم الرصيد", data='admin_balance_section')]])
            return
        try:
            star_amount = int(star_resp.text.strip())
            if star_amount <= 0:
                raise ValueError
        except ValueError:
            await conv.send_message("عدد نجوم غير صالح.", buttons=[[Button.inline("العودة لقسم الرصيد", data='admin_balance_section')]])
            return

        user_bal = get_syyad_bal(target_uid)
        user_bal['stars'] += star_amount
        save_all()
        await conv.send_message(f"تم إضافة `{star_amount}` نجمة للمستخدم `{target_uid}`. رصيده الحالي: `{user_bal['stars']}` نجمة.", buttons=[[Button.inline("العودة لقسم الرصيد", data='admin_balance_section')]])

async def hndl_a_set_sec(event):
    await event.edit(
        '**إعدادات البوت**', parse_mode='markdown',
        buttons=[
            [
                Button.inline('تحديد نقاط رابط الدعوة', 'admin_set_referral_points'),
                Button.inline('تحديد تسعيرات شحن النجوم', 'admin_set_charge_rates')
            ],
            [
                Button.inline('تحديد نقاط الهدية اليومية', 'admin_set_daily_gift_points'),
                Button.inline('تحديد وقت الحجز', 'admin_set_reservation_time')
            ],
            [
                Button.inline('تحديد قناة النشر', 'admin_set_publish_channel'),
                Button.inline('تفعيل/تعطيل التحقق', 'admin_toggle_verification')
            ],
            [
                Button.inline('الاشتراك الإجباري', 'force_sub_menu'),
                Button.inline('العودة', 'main_admin_menu')
            ]
        ]
    )

async def hndl_a_set_chan(event):
    async with client.conversation(event.sender_id, timeout=120) as conv:
        curr_chan = syyad_conf.get('publish_channel_id', 'لم يتم التعيين')
        await conv.send_message(
            f"القناة الحالية للنشر: `{curr_chan}`\n"
            "أرسل الآن معرف القناة الجديد (مثال: `@username` أو `-100123456789`). "
            "أرسل 'حذف' لإلغاء النشر التلقائي.",
            buttons=[[Button.inline("إلغاء", data='cancel_op')]]
        )
        resp = await conv.get_response()
        if resp.text == 'إلغاء':
            await conv.send_message("تم الإلغاء.", buttons=[[Button.inline("العودة لقسم الإعدادات", data='admin_settings_section')]])
            return
        
        new_chan_id = resp.text.strip()
        if new_chan_id.lower() == 'حذف':
            syyad_conf['publish_channel_id'] = None
            msg = "تم إلغاء قناة النشر."
        else:
            syyad_conf['publish_channel_id'] = new_chan_id
            msg = f"تم تحديث قناة النشر إلى `{new_chan_id}`."
        
        save_all()
        await conv.send_message(msg, buttons=[[Button.inline("العودة لقسم الإعدادات", data='admin_settings_section')]])

async def hndl_a_toggle_verification(event):
    syyad_conf['verification_enabled'] = not syyad_conf.get('verification_enabled', False)
    save_all()
    status = "مفعل" if syyad_conf['verification_enabled'] else "معطل"
    await event.answer(f"تم {'تفعيل' if syyad_conf['verification_enabled'] else 'تعطيل'} التحقق الرياضي.", alert=True)
    await hndl_a_set_sec(event)

async def hndl_a_set_ref(event):
    async with client.conversation(event.sender_id, timeout=120) as conv:
        curr_pts = syyad_conf.get('referralPoints', 0)
        await conv.send_message(
            f"النقاط الحالية لرابط الدعوة: `{curr_pts}`\n"
            f"أرسل عدد النقاط الجديدة لرابط الدعوة:",
            buttons=[[Button.inline("إلغاء", data='cancel_op')]]
        )
        user_resp = await conv.get_response()
        if user_resp.text == 'إلغاء':
            await conv.send_message(
                "تم الإلغاء.",
                buttons=[[Button.inline("العودة لقسم الإعدادات", data='admin_settings_section')]]
            )
            return
        try:
            new_pts = int(user_resp.text.strip())
            if new_pts < 0:
                raise ValueError
            syyad_conf['referralPoints'] = new_pts
            save_all()
            await conv.send_message(
                f"تم تحديث نقاط رابط الدعوة إلى `{new_pts}`.",
                buttons=[[Button.inline("العودة لقسم الإعدادات", data='admin_settings_section')]]
            )
        except ValueError:
            await conv.send_message(
                "عدد نقاط غير صالح.",
                buttons=[[Button.inline("العودة لقسم الإعدادات", data='admin_settings_section')]]
            )

async def hndl_a_add_rate(event):
    async with client.conversation(event.sender_id, timeout=120) as conv:
        await conv.send_message("أرسل عدد النقاط التي سيتم الحصول عليها:", buttons=[[Button.inline("إلغاء", data='cancel_op')]])
        pts_resp = await conv.get_response()
        if pts_resp.text == 'إلغاء':
            await conv.send_message("تم الإلغاء.", buttons=[[Button.inline("العودة لتسعيرات الشحن", data='admin_set_charge_rates')]])
            return
        try:
            pts_amount = int(pts_resp.text.strip())
            if pts_amount <= 0:
                raise ValueError
        except ValueError:
            await conv.send_message("عدد نقاط غير صالح.", buttons=[[Button.inline("العودة لتسعيرات الشحن", data='admin_set_charge_rates')]])
            return

        await conv.send_message("أرسل عدد النجوم التي يجب دفعها:", buttons=[[Button.inline("إلغاء", data='cancel_op')]])
        star_resp = await conv.get_response()
        if star_resp.text == 'إلغاء':
            await conv.send_message("تم الإلغاء.", buttons=[[Button.inline("العودة لتسعيرات الشحن", data='admin_set_charge_rates')]])
            return
        try:
            star_amount = int(star_resp.text.strip())
            if star_amount <= 0:
                raise ValueError
        except ValueError:
            await conv.send_message("عدد نجوم غير صالح.", buttons=[[Button.inline("العودة لتسعيرات الشحن", data='admin_set_charge_rates')]])
            return

        syyad_conf['chargeRates'].append({'points': pts_amount, 'stars': star_amount})
        save_all()
        await conv.send_message(f"تم إضافة تسعيرة شحن: {pts_amount} نقطة مقابل {star_amount} نجوم.", buttons=[[Button.inline("العودة لتسعيرات الشحن", data='admin_set_charge_rates')]])

async def hndl_a_del_rate(event, idx):
    if 0 <= idx < len(syyad_conf['chargeRates']):
        del_rate = syyad_conf['chargeRates'].pop(idx)
        save_all()
        await event.answer(f"تم حذف تسعيرة شحن: {del_rate['points']} نقطة مقابل {del_rate['stars']} نجوم.", alert=True)
    else:
        await event.answer("تسعيرة الشحن غير موجودة.", alert=True)
    await show_a_rates(event)

async def hndl_a_set_gift(event):
    async with client.conversation(event.sender_id, timeout=120) as conv:
        curr_pts = syyad_conf.get('dailyGiftPoints', 0)
        await conv.send_message(f"النقاط الحالية للهدية اليومية: `{curr_pts}`\nأرسل عدد النقاط الجديدة للهدية اليومية:", buttons=[[Button.inline("إلغاء", data='cancel_op')]])
        user_resp = await conv.get_response()
        if user_resp.text == 'إلغاء':
            await conv.send_message("تم الإلغاء.", buttons=[[Button.inline("العودة لقسم الإعدادات", data='admin_settings_section')]])
            return
        try:
            new_pts = int(user_resp.text.strip())
            if new_pts < 0:
                raise ValueError
            syyad_conf['dailyGiftPoints'] = new_pts
            save_all()
            await conv.send_message(f"تم تحديث نقاط الهدية اليومية إلى `{new_pts}`.", buttons=[[Button.inline("العودة لقسم الإعدادات", data='admin_settings_section')]])
        except ValueError:
            await conv.send_message("عدد نقاط غير صالح.", buttons=[[Button.inline("العودة لقسم الإعدادات", data='admin_settings_section')]])

async def hndl_a_set_time(event):
    async with client.conversation(event.sender_id, timeout=120) as conv:
        curr_mins = syyad_conf.get('reservationTimeoutMinutes', 60)
        await conv.send_message(f"الوقت الحالي لحجز الرقم: `{curr_mins}` دقيقة\nأرسل وقت الحجز الجديد بالدقائق:", buttons=[[Button.inline("إلغاء", data='cancel_op')]])
        user_resp = await conv.get_response()
        if user_resp.text == 'إلغاء':
            await conv.send_message("تم الإلغاء.", buttons=[[Button.inline("العودة لقسم الإعدادات", data='admin_settings_section')]])
            return
        try:
            new_mins = int(user_resp.text.strip())
            if new_mins <= 0:
                raise ValueError
            syyad_conf['reservationTimeoutMinutes'] = new_mins
            save_all()
            await conv.send_message(f"تم تحديث وقت حجز الرقم إلى `{new_mins}` دقيقة.", buttons=[[Button.inline("العودة لقسم الإعدادات", data='admin_settings_section')]])
        except ValueError:
            await conv.send_message("وقت غير صالح.", buttons=[[Button.inline("العودة لقسم الإعدادات", data='admin_settings_section')]])

async def hndl_u_view(event, phone, uid):
    if syyad_conf.get('force_sub_enabled', True) and force_sub_channels:
        is_subscribed = await check_force_subscription(uid)
        if not is_subscribed:
            await event.answer("❌ يجب الاشتراك في القنوات أولاً!", alert=True)
            await send_force_sub_message(uid)
            return
    
    if phone in avail_nums:
        details = avail_nums[phone]
        status = details.get('status')
        pts_price = details.get('price_points', 0)
        star_price = details.get('price_stars', 0)

        message = (
            f"**تفاصيل الرقم `{mask_phone_number(phone)}`:**\n\n"
            f"🌍 الدولة: {details['country']}\n"
        )
        if pts_price > 0:
            message += f"💰 السعر بالنقاط: `{pts_price}`\n"
        if star_price > 0:
            message += f"🌟 السعر بالنجوم: `{star_price}`\n"

        buttons = []
        action_btns = []
        if status == 'available':
            if star_price > 0 and syyad_conf.get('reservationTimeoutMinutes', 0) > 0:
                action_btns.append(Button.inline(f"حجز الرقم ({star_price // 2:.0f} نجوم)", data=f"book_number:{phone}"))
            if pts_price > 0 or star_price > 0:
                action_btns.append(Button.inline("شراء الآن", data=f"choose_payment_method:{phone}:full"))
            if action_btns:
                buttons.append(action_btns)
        elif status == 'booked' and str(details.get('booked_by')) == uid:
            rem_star_amount = star_price - details.get('deposit_paid_stars', 0)
            message += (
                f"**حالة الحجز:** محجوز لك!\n"
                f"مبلغ الحجز المدفوع: `{details.get('deposit_paid_stars', 0)}` نجوم\n"
            )
            if details.get('expiry_time'):
                rem_sec = max(0, int(details['expiry_time'] - time.time()))
                mins = rem_sec // 60
                secs = rem_sec % 60
                message += f"الوقت المتبقي: `{mins:02d}:{secs:02d}` دقيقة\n\n"

            if rem_star_amount > 0:
                action_btns.append(Button.inline(f"إتمام الشراء ({rem_star_amount:.0f} نجوم)", data=f"choose_payment_method:{phone}:remaining"))
            if pts_price > 0:
                 action_btns.append(Button.inline(f"إتمام الشراء ({pts_price} نقاط)", data=f"choose_payment_method:{phone}:points_only"))
            
            if action_btns:
                buttons.append(action_btns)
            
            buttons.append([Button.inline("إلغاء الحجز", data=f"user_cancel_booking:{phone}")])
        elif status == 'booked' and str(details.get('booked_by')) != uid:
             await event.answer("هذا الرقم محجوز لمستخدم آخر حالياً.", alert=True)
             await show_u_ctry(event)
             return
        elif status == 'sold':
            await event.answer("هذا الرقم مباع بالفعل.", alert=True)
            await show_u_ctry(event)
            return

        buttons.append([Button.inline("العودة لقائمة الدول", data="user_buy_number_menu")])
        await event.edit(message, parse_mode='markdown', buttons=buttons)
    else:
        await event.answer("الرقم لم يعد متاحاً.", alert=True)
        await show_u_ctry(event)

async def hndl_u_book(event, phone):
    uid = str(event.sender_id)
    if syyad_conf.get('force_sub_enabled', True) and force_sub_channels:
        is_subscribed = await check_force_subscription(uid)
        if not is_subscribed:
            await event.answer("❌ يجب الاشتراك في القنوات أولاً!", alert=True)
            await send_force_sub_message(uid)
            return
    
    if phone not in avail_nums or avail_nums[phone]['status'] != 'available':
        await event.answer("الرقم غير متاح للحجز.", alert=True)
        await show_u_ctry(event)
        return

    details = avail_nums[phone]
    full_price = details.get('price_stars', 0)
    if full_price == 0:
        await event.answer("لا يمكن حجز هذا الرقم بالنجوم (لا يوجد سعر بالنجوم).", alert=True)
        await show_u_ctry(event)
        return

    dep_amount = max(1, full_price // 2)
    prices = [LabeledPrice(label=f"حجز الرقم {mask_phone_number(phone)} (نصف السعر)", amount=dep_amount)]
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        lambda: bot.send_invoice(
            chat_id=event.sender_id,
            title=f"حجز الرقم {mask_phone_number(phone)}",
            description=f"دفع نصف سعر الرقم ({dep_amount} نجوم) لحجزه لمدة {syyad_conf.get('reservationTimeoutMinutes', 60)} دقيقة.",
            provider_token=pay_token,
            currency="XTR",
            prices=prices,
            start_parameter=f"book_number_{phone.replace('+', '')}",
            invoice_payload=f"book_number:{phone}:{dep_amount}"
        )
    )
    await event.answer("جارٍ إعداد عملية الدفع للحجز...", alert=True)

async def hndl_u_endb_conf(event, phone, uid):
    if syyad_conf.get('force_sub_enabled', True) and force_sub_channels:
        is_subscribed = await check_force_subscription(uid)
        if not is_subscribed:
            await event.answer("❌ يجب الاشتراك في القنوات أولاً!", alert=True)
            await send_force_sub_message(uid)
            return
    
    if phone in avail_nums and avail_nums[phone]['status'] == 'booked' and str(avail_nums[phone]['booked_by']) == uid:
        buttons = [
            [
                Button.inline("نعم، إلغاء الحجز", data=f"execute_user_cancel_booking:{phone}"),
                Button.inline("لا، العودة", data=f"view_number_details:{phone}")
            ]
        ]
        await event.edit("هل أنت متأكد من إلغاء حجز الرقم؟ لن يتم استرداد مبلغ الحجز.", buttons=buttons)
    else:
        await event.answer("هذا الرقم ليس محجوزاً لك.", alert=True)
        await show_u_ctry(event)

async def hndl_u_endb_exec(event, phone, uid):
    if syyad_conf.get('force_sub_enabled', True) and force_sub_channels:
        is_subscribed = await check_force_subscription(uid)
        if not is_subscribed:
            await event.answer("❌ يجب الاشتراك في القنوات أولاً!", alert=True)
            await send_force_sub_message(uid)
            return
    
    if phone in avail_nums and avail_nums[phone]['status'] == 'booked' and str(avail_nums[phone]['booked_by']) == uid:
        await end_resv(phone)
        await event.answer("تم إلغاء الحجز بنجاح.", alert=True)
        await show_u_ctry(event)
    else:
        await event.answer("هذا الرقم ليس محجوزاً لك أو الحجز انتهى.", alert=True)
        await show_u_ctry(event)

async def hndl_u_pay_meth(event, phone, pay_type, uid):
    if syyad_conf.get('force_sub_enabled', True) and force_sub_channels:
        is_subscribed = await check_force_subscription(uid)
        if not is_subscribed:
            await event.answer("❌ يجب الاشتراك في القنوات أولاً!", alert=True)
            await send_force_sub_message(uid)
            return
    
    if phone not in avail_nums:
        await event.answer("الرقم لم يعد متاحاً.", alert=True)
        await show_u_ctry(event)
        return

    details = avail_nums[phone]
    user_bal = get_syyad_bal(uid)

    pts_price = details.get('price_points', 0)
    star_price = details.get('price_stars', 0)
    star_to_pay = 0
    pts_to_pay = 0

    if pay_type == 'remaining':
        if not (details.get('status') == 'booked' and str(details.get('booked_by')) == uid):
            await event.answer("هذا الرقم ليس محجوزاً لك لإتمام الشراء.", alert=True)
            await show_u_ctry(event)
            return
        dep_paid = details.get('deposit_paid_stars', 0)
        star_to_pay = star_price - dep_paid
        pts_to_pay = pts_price
    elif pay_type == 'full':
        if details.get('status') != 'available':
            await event.answer("هذا الرقم غير متاح للشراء المباشر.", alert=True)
            await show_u_ctry(event)
            return
        star_to_pay = star_price
        pts_to_pay = pts_price
    elif pay_type == 'points_only':
        if not (details.get('status') == 'booked' and str(details.get('booked_by')) == uid):
            await event.answer("هذا الرقم ليس محجوزاً لك لإتمام الشراء.", alert=True)
            await show_u_ctry(event)
            return
        star_to_pay = 0
        pts_to_pay = pts_price

    message = f"اختر طريقة الدفع للرقم `{mask_phone_number(phone)}`:\n"
    buttons = []
    pay_row = []

    if pts_to_pay > 0:
        message += f"**السعر بالنقاط:** `{pts_to_pay}` (رصيدك: `{user_bal['points']}`)\n"
        pay_row.append(Button.inline(f"دفع {pts_to_pay} نقطة", data=f"pay_with_points:{phone}:{pay_type}"))
    if star_to_pay > 0:
        message += f"**السعر بالنجوم:** `{star_to_pay}`\n"
        pay_row.append(Button.inline(f"دفع {star_to_pay} نجمة", data=f"pay_with_stars:{phone}:{star_to_pay}"))

    if not pay_row:
        await event.answer("لا يوجد مبلغ متبقي للدفع.", alert=True)
        await hndl_u_view(event, phone, uid)
        return

    buttons.append(pay_row)
    buttons.append([Button.inline("إلغاء", data=f"view_number_details:{phone}")])
    await event.edit(message, parse_mode='markdown', buttons=buttons)

async def hndl_u_pay_pts(event, phone, pay_type, uid):
    if syyad_conf.get('force_sub_enabled', True) and force_sub_channels:
        is_subscribed = await check_force_subscription(uid)
        if not is_subscribed:
            await event.answer("❌ يجب الاشتراك في القنوات أولاً!", alert=True)
            await send_force_sub_message(uid)
            return
    
    if phone not in avail_nums:
        await event.answer("الرقم لم يعد متاحاً.", alert=True)
        await show_u_ctry(event)
        return

    details = avail_nums[phone]
    user_bal = get_syyad_bal(uid)
    
    pts_to_pay = 0
    if pay_type in ['remaining', 'points_only', 'full']:
        pts_to_pay = details.get('price_points', 0)

    if pts_to_pay > 0 and user_bal['points'] >= pts_to_pay:
        user_bal['points'] -= pts_to_pay

        is_booked = (pay_type in ['remaining', 'points_only']) and details.get('status') == 'booked'
        is_full = pay_type == 'full' and details.get('status') == 'available'

        if is_booked or is_full:
            avail_nums[phone]['status'] = 'sold'
            avail_nums[phone]['buyer_id'] = uid
            code_reqs[phone] = event.sender_id

            if pay_type == 'full':
                user_bal['new_numbers'].append(phone)
            else:
                user_bal['old_numbers'].append(phone)
            
            if is_booked:
                await end_resv(phone, notify=False)
            
            save_all()
            await edit_post(phone)

            await event.edit(
                f"تمت عملية الشراء بنجاح للرقم `{phone}`.\n\n"
                "يرجى الآن محاولة تسجيل الدخول بالرقم. سيصلك كود الدخول وكلمة المرور هنا فوراً.",
                parse_mode='markdown'
            )
            pay_method = "بالنقاط + حجز النجوم" if is_booked else "بالنقاط"
            await client.send_message(
                int(syyad_conf['admin_ids'][0]),
                f"تم شراء الرقم `{phone}` بواسطة `{uid}` ({pay_method}).",
                parse_mode='markdown'
            )
    else:
        await event.answer("نقاطك غير كافية لإتمام عملية الشراء.", alert=True)
        await event.edit("نقاطك غير كافية.", buttons=[
            [Button.inline("شحن نقاط", data='user_charge_points_menu')], 
            [Button.inline("العودة", data=f"view_number_details:{phone}")]
        ])

async def hndl_u_pay_star(event, phone, amount):
    uid = str(event.sender_id)
    if syyad_conf.get('force_sub_enabled', True) and force_sub_channels:
        is_subscribed = await check_force_subscription(uid)
        if not is_subscribed:
            await event.answer("❌ يجب الاشتراك في القنوات أولاً!", alert=True)
            await send_force_sub_message(uid)
            return
    
    if phone not in avail_nums:
        await event.answer("الرقم لم يعد متاحاً.", alert=True)
        await show_u_ctry(event)
        return

    prices = [LabeledPrice(label=f"شراء الرقم {mask_phone_number(phone)}", amount=amount)]
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        lambda: bot.send_invoice(
            chat_id=event.sender_id,
            title=f"شراء الرقم {mask_phone_number(phone)}",
            description=f"دفع {amount} نجوم لإتمام شراء الرقم {mask_phone_number(phone)}.",
            provider_token=pay_token,
            currency="XTR",
            prices=prices,
            start_parameter=f"buy_number_{phone.replace('+', '')}",
            invoice_payload=f"buy_number:{phone}:{amount}"
        )
    )
    await event.answer("جارٍ إعداد عملية الدفع بالنجوم...", alert=True)

async def hndl_u_get_ref(event, uid):
    if syyad_conf.get('force_sub_enabled', True) and force_sub_channels:
        is_subscribed = await check_force_subscription(uid)
        if not is_subscribed:
            await event.answer("❌ يجب الاشتراك في القنوات أولاً!", alert=True)
            await send_force_sub_message(uid)
            return
    
    bot_info = await client.get_me()
    bot_user = bot_info.username
    ref_link = f"https://t.me/{bot_user}?start=ref_{uid}"
    
    campaign_enabled = syyad_conf.get('referral_campaign_enabled', False)
    campaign_points = syyad_conf.get('referral_campaign_points', 0)
    regular_points = syyad_conf.get('referralPoints', 0)
    
    points_info = f"`{regular_points}` نقطة"
    if campaign_enabled:
        points_info = f"🎯 **{campaign_points} نقطة (حملة نشطة!)**"
    
    await event.edit(
        f"**رابط الإحالة الخاص بك:**\n`{ref_link}`\n\n"
        f"شارك هذا الرابط مع أصدقائك. ستحصل على {points_info} لكل مستخدم جديد يسجل عبر رابطك.\n\n"
        f"**عدد الإحالات الحالي:** `{syyad_users.get(uid, {}).get('referral_count', 0)}`",
        parse_mode='markdown',
        buttons=[[Button.inline("العودة", data="user_charge_points_menu")]]
    )

async def hndl_u_chrg_star(event, idx):
    uid = str(event.sender_id)
    if syyad_conf.get('force_sub_enabled', True) and force_sub_channels:
        is_subscribed = await check_force_subscription(uid)
        if not is_subscribed:
            await event.answer("❌ يجب الاشتراك في القنوات أولاً!", alert=True)
            await send_force_sub_message(uid)
            return
    
    if 0 <= idx < len(syyad_conf['chargeRates']):
        rate = syyad_conf['chargeRates'][idx]
        prices = [LabeledPrice(label=f"شحن {rate['points']} نقطة", amount=rate['stars'])]
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: bot.send_invoice(
                chat_id=event.sender_id,
                title=f"شحن نقاط",
                description=f"شحن {rate['points']} نقطة مقابل {rate['stars']} نجوم.",
                provider_token=pay_token,
                currency="XTR",
                prices=prices,
                start_parameter=f"charge_stars_{rate['points']}",
                invoice_payload=f"charge_stars:{rate['points']}:{rate['stars']}"
            )
        )
        await event.answer("جارٍ إعداد عملية الدفع بالنجوم...", alert=True)
    else:
        await event.answer("تسعيرة الشحن غير موجودة.", alert=True)
        await show_u_chrg(event)

async def hndl_u_gift(event, uid):
    if syyad_conf.get('force_sub_enabled', True) and force_sub_channels:
        is_subscribed = await check_force_subscription(uid)
        if not is_subscribed:
            await event.answer("❌ يجب الاشتراك في القنوات أولاً!", alert=True)
            await send_force_sub_message(uid)
            return
    
    user_bal = get_syyad_bal(uid)
    curr_time = time.time()
    last_claim = user_bal.get('lastDailyGiftClaim')
    gift_pts = syyad_conf.get('dailyGiftPoints', 0)

    if gift_pts == 0:
        await event.answer("الهدية اليومية غير متاحة حالياً.", alert=True)
        return

    if last_claim and (curr_time - last_claim) < 86400:
        next_claim = last_claim + 86400
        rem = int(next_claim - curr_time)
        mins, secs = divmod(rem, 60)
        hours, mins = divmod(mins, 60)
        await event.answer(f"لقد حصلت على هديتك اليومية بالفعل. يمكنك المطالبة بالهدية التالية بعد: {hours:02d} ساعة و {mins:02d} دقيقة.", alert=True)
    else:
        user_bal['points'] += gift_pts
        user_bal['lastDailyGiftClaim'] = curr_time
        save_all()
        await event.answer(f"🎉 تهانينا! لقد حصلت على `{gift_pts}` نقطة كهدية يومية!", alert=True)
        await show_u_main(event)

@client.on(events.NewMessage)
async def handle_verification(event):
    uid = str(event.sender_id)
    
    if is_adm(uid) or is_owner(uid):
        return
    
    if uid in user_verifications and syyad_conf.get('verification_enabled', True):
        verification = user_verifications[uid]
        
        if verification['attempts'] >= verification['max_attempts']:
            del user_verifications[uid]
            await event.reply("❌ لقد تجاوزت عدد المحاولات المسموح بها. الرجاء المحاولة مرة أخرى.")
            return
        
        user_answer = event.text.strip()
        
        if user_answer == verification['answer']:
            del user_verifications[uid]
            mark_user_verified(uid)
            
            if syyad_conf.get('force_sub_enabled', True) and force_sub_channels:
                is_subscribed = await check_force_subscription(uid)
                if not is_subscribed:
                    await send_force_sub_message(uid)
                    return
            
            await event.reply("✅ تحقق ناجح! يمكنك الآن استخدام البوت.")
            
            if is_adm(event.sender_id):
                await hndl_a_main(event)
            else:
                await show_u_main(event)
        else:
            verification['attempts'] += 1
            remaining = verification['max_attempts'] - verification['attempts']
            await event.reply(f"❌ إجابة خاطئة. المحاولات المتبقية: {remaining}")
    
    elif syyad_conf.get('verification_enabled', True) and not is_user_verified(uid) and not is_adm(uid):
        if syyad_conf.get('force_sub_enabled', True) and force_sub_channels:
            is_subscribed = await check_force_subscription(uid)
            if not is_subscribed:
                await send_force_sub_message(uid)
                return
        
        verification_data, message = await ask_verification(uid)
        user_verifications[uid] = verification_data
        await event.reply(message, parse_mode='markdown')

@client.on(events.NewMessage(pattern=r'/start(?: (point_|ref_)(\w+))?'))
async def hndl_start(event):
    uid = str(event.sender_id)
    start_type = event.pattern_match.group(1)
    param_value = event.pattern_match.group(2)
    
    user_info = await get_user_info(uid)
    await log_user_login(uid, user_info.get('username'), user_info.get('first_name'), user_info.get('last_name'))
    
    if syyad_conf.get('force_sub_enabled', True) and force_sub_channels:
        is_subscribed = await check_force_subscription(uid)
        if not is_subscribed:
            await send_force_sub_message(uid)
            return
    
    if not (is_adm(uid) or is_owner(uid)):
        if syyad_conf.get('verification_enabled', True) and not is_user_verified(uid):
            verification_data, message = await ask_verification(uid)
            user_verifications[uid] = verification_data
            await event.reply(message, parse_mode='markdown')
            return

    is_new = uid not in syyad_users
    get_syyad_bal(uid)
    
    if is_new:
        await send_welcome_message(uid, user_info)
    
    if start_type == 'point_':
        link_id = param_value
        if link_id in point_links:
            link_data = point_links[link_id]
            
            if link_data['max_uses'] > 0 and link_data['current_uses'] >= link_data['max_uses']:
                await event.reply("❌ هذا الرابط قد استنفذ عدد الاستخدامات المسموح به.")
                return
            
            if uid in link_data['used_by']:
                await event.reply("⚠️ لقد استخدمت هذا الرابط من قبل.")
                return
            
            user_bal = get_syyad_bal(uid)
            user_bal['points'] += link_data['points']
            
            link_data['current_uses'] += 1
            link_data['used_by'].append(uid)
            save(POINT_LINKS_FILE, point_links)
            
            await event.reply(
                f"🎉 **تهانينا!**\n\n"
                f"لقد حصلت على `{link_data['points']}` نقطة من رابط النقاط.\n"
                f"رصيدك الحالي: `{user_bal['points']}` نقطة."
            )
            
            try:
                await client.send_message(
                    int(link_data['creator_id']),
                    f"🔗 **تم استخدام رابطك!**\n\n"
                    f"المستخدم: `{uid}`\n"
                    f"النقاط: `{link_data['points']}`\n"
                    f"الاستخدام الحالي: `{link_data['current_uses']}`/{'∞' if link_data['max_uses'] == 0 else link_data['max_uses']}"
                )
            except:
                pass
    
    elif start_type == 'ref_':
        ref_id = param_value
        if is_new and ref_id and ref_id != uid:
            if 'referred_by' not in syyad_users.get(uid, {}):
                campaign_enabled = syyad_conf.get('referral_campaign_enabled', False)
                campaign_users = syyad_conf.get('referral_campaign_users', 0)
                max_referrals = syyad_conf.get('max_referrals_per_user', 0)
                
                get_syyad_bal(ref_id)
                syyad_users[uid]['referred_by'] = ref_id
                
                if campaign_enabled and (campaign_users == 0 or syyad_users[ref_id]['referral_count'] < campaign_users):
                    if max_referrals == 0 or syyad_users[ref_id]['referral_count'] < max_referrals:
                        ref_pts = syyad_conf.get('referral_campaign_points', 0)
                    else:
                        ref_pts = syyad_conf.get('referralPoints', 0)
                else:
                    ref_pts = syyad_conf.get('referralPoints', 0)
                
                if ref_pts > 0:
                    syyad_users[ref_id]['points'] += ref_pts
                    syyad_users[ref_id]['referral_count'] += 1
                    syyad_users[ref_id]['total_earned_from_referrals'] = syyad_users[ref_id].get('total_earned_from_referrals', 0) + ref_pts
                    save_all()
                    await client.send_message(int(ref_id), f"🎉 لقد ربحت `{ref_pts}` نقطة من إحالة مستخدم جديد!")

    await calculate_daily_ranking()
    
    if is_adm(event.sender_id):
        await hndl_a_main(event)
    else:
        await show_u_main(event)

@client.on(events.CallbackQuery)
async def hndl_cb(event):
    uid = str(event.sender_id)
    data = event.data.decode()

    if data == 'dummy_sep':
        await event.answer()
        return
    
    if syyad_conf.get('force_sub_enabled', True) and force_sub_channels and data not in ['check_subscription', 'cancel_op']:
        is_subscribed = await check_force_subscription(uid)
        if not is_subscribed:
            await event.answer("❌ يجب الاشتراك في القنوات أولاً!", alert=True)
            await send_force_sub_message(uid)
            return

    if data == 'check_subscription':
        is_subscribed = await check_force_subscription(uid)
        if is_subscribed:
            user_bal = get_syyad_bal(uid)
            user_bal['force_sub_checked'] = True
            save_all()
            await event.answer("✅ تم التحقق من الاشتراك بنجاح!", alert=True)
            if is_adm(uid):
                await hndl_a_main(event)
            else:
                await show_u_main(event)
        else:
            await event.answer("❌ لم تشترك في جميع القنوات المطلوبة.", alert=True)
            await send_force_sub_message(uid)

    elif data == 'cancel_op':
        if is_adm(uid):
            await event.edit("تم الإلغاء.", buttons=[[Button.inline("العودة", data='main_admin_menu')]])
        else:
            await event.edit("تم الإلغاء.", buttons=[[Button.inline("العودة", data='user_main_menu')]])

    elif is_adm(uid):
        if data == 'main_admin_menu': 
            await hndl_a_main(event)
        elif data == 'admin_stats': 
            await hndl_a_stats(event)
        elif data == 'admin_user_log':
            await hndl_user_login_log(event)
        elif data == 'show_all_users':
            await hndl_show_all_users(event)
        elif data == 'admin_numbers_section': 
            await hndl_a_nums(event)
        elif data == 'add_new_number': 
            await hndl_a_add(event)
        elif data == 'view_added_numbers': 
            await show_a_nums(event)
        elif data.startswith('view_specific_number:'): 
            await hndl_a_view_num(event, data.split(':', 1)[1])
        elif data.startswith('admin_cancel_booking:'): 
            await hndl_a_end_book(event, data.split(':', 1)[1])
        elif data == 'delete_displayed_numbers': 
            await show_a_del(event)
        elif data.startswith('delete_number_confirm:'): 
            await hndl_a_del_conf(event, data.split(':', 1)[1])
        elif data.startswith('delete_number_execute:'): 
            await hndl_a_del_exec(event, data.split(':', 1)[1])
        elif data == 'admin_admins_section': 
            await hndl_a_adm_sec(event)
        elif data == 'admin_promote_admin': 
            await hndl_a_promo(event)
        elif data == 'admin_demote_admin': 
            await hndl_a_demote(event)
        elif data == 'admin_view_admins': 
            await show_a_list(event)
        elif data == 'admin_sales_section': 
            await hndl_a_sale_sec(event)
        elif data == 'admin_view_sold_numbers': 
            await hndl_a_sold(event)
        elif data == 'admin_view_available_numbers': 
            await hndl_a_avail(event)
        elif data == 'admin_balance_section': 
            await hndl_a_bal_sec(event)
        elif data == 'admin_add_points': 
            await hndl_a_add_pts(event)
        elif data == 'admin_add_stars': 
            await hndl_a_add_star(event)
        elif data == 'admin_settings_section': 
            await hndl_a_set_sec(event)
        elif data == 'admin_set_referral_points': 
            await hndl_a_set_ref(event)
        elif data == 'admin_set_charge_rates': 
            await show_a_rates(event)
        elif data == 'add_charge_rate': 
            await hndl_a_add_rate(event)
        elif data.startswith('delete_charge_rate:'): 
            await hndl_a_del_rate(event, int(data.split(':', 1)[1]))
        elif data == 'admin_set_daily_gift_points': 
            await hndl_a_set_gift(event)
        elif data == 'admin_set_reservation_time': 
            await hndl_a_set_time(event)
        elif data == 'admin_set_publish_channel': 
            await hndl_a_set_chan(event)
        elif data == 'admin_toggle_verification': 
            await hndl_a_toggle_verification(event)
        elif data == 'force_sub_menu': 
            await hndl_force_sub_menu(event)
        elif data == 'add_force_sub_channel': 
            await hndl_add_force_sub(event)
        elif data == 'remove_force_sub_channel': 
            await hndl_remove_force_sub(event)
        elif data.startswith('remove_force_sub_confirm:'): 
            await hndl_remove_force_sub_confirm(event, data.split(':', 1)[1])
        elif data.startswith('remove_force_sub_execute:'): 
            await hndl_remove_force_sub_execute(event, data.split(':', 1)[1])
        elif data == 'show_force_sub_channels': 
            await hndl_show_force_sub_channels(event)
        elif data == 'disable_force_sub': 
            await hndl_toggle_force_sub(event)
        elif data == 'enable_force_sub': 
            await hndl_toggle_force_sub(event)
        elif data == 'broadcast_menu': 
            await hndl_broadcast_menu(event)
        elif data == 'send_broadcast_message': 
            await hndl_send_broadcast_message(event)
        elif data.startswith('confirm_broadcast:'): 
            await hndl_confirm_broadcast(event, *data.split(':', 2)[1:])
        elif data == 'show_broadcast_history': 
            await hndl_show_broadcast_history(event)
        elif data == 'point_links_menu': 
            await hndl_point_links_menu(event)
        elif data == 'create_point_link': 
            await hndl_create_point_link(event)
        elif data == 'my_point_links': 
            await hndl_my_point_links(event)
        elif data == 'point_links_stats': 
            await hndl_point_links_stats(event)
    else:
        if data == 'user_main_menu': 
            await show_u_main(event)
        elif data == 'user_buy_number_menu': 
            await show_u_ctry(event)
        elif data.startswith('show_country_numbers:'): 
            await show_u_nums(event, data.split(':', 1)[1])
        elif data.startswith('view_number_details:'): 
            await hndl_u_view(event, data.split(':', 1)[1], uid)
        elif data.startswith('book_number:'): 
            await hndl_u_book(event, data.split(':', 1)[1])
        elif data.startswith('user_cancel_booking:'): 
            await hndl_u_endb_conf(event, data.split(':', 1)[1], uid)
        elif data.startswith('execute_user_cancel_booking:'): 
            await hndl_u_endb_exec(event, data.split(':', 1)[1], uid)
        elif data.startswith('choose_payment_method:'): 
            await hndl_u_pay_meth(event, *data.split(':', 2)[1:], uid)
        elif data.startswith('pay_with_points:'): 
            await hndl_u_pay_pts(event, *data.split(':', 2)[1:], uid)
        elif data.startswith('pay_with_stars:'): 
            await hndl_u_pay_star(event, data.split(':', 2)[1], int(data.split(':', 2)[2]))
        elif data == 'user_charge_points_menu': 
            await show_u_chrg(event)
        elif data == 'user_get_referral_link': 
            await hndl_u_get_ref(event, uid)
        elif data == 'user_charge_by_stars_menu': 
            await show_u_star(event)
        elif data.startswith('charge_by_stars:'): 
            await hndl_u_chrg_star(event, int(data.split(':', 1)[1]))
        elif data == 'user_daily_gift': 
            await hndl_u_gift(event, uid)
        elif data == 'user_my_numbers': 
            await show_user_numbers_menu(event, uid)
        elif data == 'user_show_old_numbers': 
            await show_user_numbers_list(event, uid, "old")
        elif data == 'user_show_new_numbers': 
            await show_user_numbers_list(event, uid, "new")
        elif data == 'user_show_points': 
            await show_u_points(event, uid)
        elif data == 'show_top_users': 
            await show_top_users(event)

@bot.pre_checkout_query_handler(func=lambda query: True)
def hndl_pre_cq(pre_cq):
    bot.answer_pre_checkout_query(pre_cq.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def hndl_paid(paid_msg):
    uid = str(paid_msg.chat.id)
    syyad_payload = paid_msg.successful_payment.invoice_payload

    if syyad_payload.startswith("book_number:"):
        _, phone, dep_star_str = syyad_payload.split(':')
        dep_star_amount = int(dep_star_str)

        if phone in avail_nums and avail_nums[phone]['status'] == 'available':
            res_timeout = syyad_conf.get('reservationTimeoutMinutes', 60)
            expiry_time = time.time() + (res_timeout * 60)

            avail_nums[phone].update({
                'status': 'booked',
                'booked_by': uid,
                'booking_time': time.time(),
                'expiry_time': expiry_time,
                'deposit_paid_stars': dep_star_amount
            })
            save_all()

            asyncio.run_coroutine_threadsafe(run_timer(phone, uid, expiry_time), client.loop)

            bot.send_message(uid, f"✅ تم حجز الرقم `{mask_phone_number(phone)}` بنجاح!\n"
                                             f"لقد دفعت `{dep_star_amount}` نجمة.\n"
                                             f"الرجاء إتمام عملية الشراء خلال `{res_timeout}` دقيقة بدفع باقي المبلغ.")
            bot.send_message(int(syyad_conf['admin_ids'][0]), f"🔔 تم حجز الرقم `{phone}` بواسطة `{uid}` (دفعة حجز: {dep_star_amount} نجوم). سينتهي الحجز في {datetime.datetime.fromtimestamp(expiry_time).strftime('%Y-%m-%d %H:%M:%S')}.")
        else:
            bot.send_message(uid, "❌ فشل حجز الرقم. الرقم غير متاح أو تم حجزه من قبل.")
            bot.send_message(int(syyad_conf['admin_ids'][0]), f"⚠️ فشلت محاولة حجز الرقم `{phone}` بواسطة `{uid}` (الرقم غير متاح).")

    elif syyad_payload.startswith("buy_number:"):
        _, phone, paid_star_str = syyad_payload.split(':')
        paid_star_amount = int(paid_star_str)

        if phone in avail_nums:
            details = avail_nums[phone]
            success = False
            method = ""
            num_type = ""

            if details['status'] == 'booked' and str(details['booked_by']) == uid:
                req_amount = details['price_stars'] - details.get('deposit_paid_stars', 0)
                if paid_star_amount >= req_amount:
                    success = True
                    method = f"إتمام حجز ({paid_star_amount} نجوم)"
                    num_type = "old"
                    asyncio.run_coroutine_threadsafe(end_resv(phone, notify=False), client.loop)
            elif details['status'] == 'available':
                req_amount = details.get('price_stars', 0)
                if paid_star_amount >= req_amount:
                    success = True
                    method = f"شراء مباشر ({paid_star_amount} نجوم)"
                    num_type = "new"

            if success:
                bot.send_message(uid, f"✅ تهانينا! تم شراء الرقم `{phone}` بنجاح.\n"
                                                  "يرجى الآن محاولة تسجيل الدخول بالرقم. سيصلك كود الدخول وكلمة المرور هنا فوراً.")
                avail_nums[phone]['status'] = 'sold'
                avail_nums[phone]['buyer_id'] = uid
                code_reqs[phone] = paid_msg.chat.id
                
                user_bal = get_syyad_bal(uid)
                if num_type == "new":
                    user_bal['new_numbers'].append(phone)
                else:
                    user_bal['old_numbers'].append(phone)
                
                save_all()
                asyncio.run_coroutine_threadsafe(edit_post(phone), client.loop)
                bot.send_message(int(syyad_conf['admin_ids'][0]), f"🎉 تم شراء الرقم `{phone}` بنجاح من قبل `{uid}` ({method}).")
            else:
                bot.send_message(uid, "❌ خطأ في الدفع. المبلغ المدفوع غير كافٍ أو حالة الرقم خاطئة.")
                bot.send_message(int(syyad_conf['admin_ids'][0]), f"⚠️ خطأ في دفع الرقم `{phone}` بواسطة `{uid}`.")
        else:
            bot.send_message(uid, "❌ فشل الشراء. الرقم لم يعد متاحاً.")
            bot.send_message(int(syyad_conf['admin_ids'][0]), f"⚠️ فشلت محاولة شراء الرقم `{phone}` بواسطة `{uid}` (الرقم غير موجود).")

    elif syyad_payload.startswith("charge_stars:"):
        _, pts_str, star_str = syyad_payload.split(':')
        pts_added = int(pts_str)
        star_paid = int(star_str)

        user_bal = get_syyad_bal(uid)
        user_bal['points'] += pts_added
        save_all()

        bot.send_message(uid, f"✅ تم شحن `{pts_added}` نقطة بنجاح مقابل `{star_paid}` نجمة. رصيدك الحالي: `{user_bal['points']}` نقطة.")
        bot.send_message(int(syyad_conf['admin_ids'][0]), f"🌟 تم شحن `{pts_added}` نقطة للمستخدم `{uid}` مقابل `{star_paid}` نجمة.")
    else:
        bot.send_message(uid, "تم الدفع بنجاح، ولكن لم يتم تحديد الغرض.")

async def run_syyad_app():
    load_all()

    await client.start(bot_token=BOT_TOKEN)
    await run_accs()
    await init_resv()

    poll_thread = threading.Thread(target=run_poll, daemon=True)
    poll_thread.start()

    await client.run_until_disconnected()

if __name__ == '__main__':
    try:
        asyncio.run(run_syyad_app())
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        save_all()
        #حقوق كاسبر لحد يغير الحقوق لا محلل ولا موهوم وبذمته