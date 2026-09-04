import os
import threading
from flask import Flask, request, render_template_string
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from PIL import Image, ImageDraw, ImageFont
import io

# Nhận Token và Link Web từ máy chủ Render
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
WEB_URL = os.environ.get('WEB_URL', '') 

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Ghép Ảnh FC Mobile</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { font-family: Arial, sans-serif; background-color: var(--tg-theme-bg-color, #f4f4f9); color: var(--tg-theme-text-color, #000); padding: 20px; margin: 0; }
        .container { background: var(--tg-theme-secondary-bg-color, #fff); padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        h2 { text-align: center; color: #2196F3; }
        label { font-weight: bold; display: block; margin-top: 15px; margin-bottom: 5px;}
        input[type="file"], input[type="text"] { width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; margin-top: 25px; background-color: var(--tg-theme-button-color, #2196F3); color: var(--tg-theme-button-text-color, #fff); border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; }
        button:active { opacity: 0.8; }
        .loading { display: none; text-align: center; margin-top: 15px; color: #ff9800; font-weight: bold;}
    </style>
</head>
<body>
    <div class="container">
        <h2>TOOL GHÉP ẢNH</h2>
        <form id="uploadForm" enctype="multipart/form-data">
            <input type="hidden" id="chat_id" name="chat_id">
            
            <label>1. Chọn các ảnh (Ít nhất 2 ảnh):</label>
            <input type="file" id="images" name="images" accept="image/*" multiple required>
            
            <label>2. Chữ góc trên (VD: Ms1377):</label>
            <input type="text" name="text1" placeholder="Bỏ trống nếu không chèn">
            
            <label>3. Chữ góc dưới (VD: Login...):</label>
            <input type="text" name="text2" placeholder="Bỏ trống nếu không chèn">
            
            <button type="submit" id="submitBtn">TIẾN HÀNH GHÉP ẢNH</button>
            <div id="loading" class="loading">⏳ Đang xử lý và gửi ảnh về Chat... Vui lòng đợi!</div>
        </form>
    </div>

    <script>
        let tg = window.Telegram.WebApp;
        tg.expand();
        if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
            document.getElementById('chat_id').value = tg.initDataUnsafe.user.id;
        } else {
            document.getElementById('chat_id').value = "0"; 
        }

        document.getElementById('uploadForm').addEventListener('submit', function(e) {
            e.preventDefault();
            if(document.getElementById('images').files.length < 2) {
                tg.showAlert("Vui lòng chọn ít nhất 2 ảnh!"); return;
            }
            document.getElementById('submitBtn').style.display = 'none';
            document.getElementById('loading').style.display = 'block';
            let formData = new FormData(this);

            fetch('/api/process', { method: 'POST', body: formData })
            .then(response => response.json())
            .then(data => {
                if(data.success) {
                    tg.showAlert("✅ Thành công! Hãy đóng Mini App và kiểm tra tin nhắn Bot.");
                    tg.close();
                } else {
                    tg.showAlert("❌ Lỗi: " + data.message);
                    document.getElementById('submitBtn').style.display = 'block';
                    document.getElementById('loading').style.display = 'none';
                }
            }).catch(error => {
                tg.showAlert("❌ Lỗi kết nối!");
                document.getElementById('submitBtn').style.display = 'block';
                document.getElementById('loading').style.display = 'none';
            });
        });
    </script>
</body>
</html>
'''

@app.route('/')
def mini_app_home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/process', methods=['POST'])
def process_images():
    try:
        chat_id = request.form.get('chat_id')
        text1 = request.form.get('text1', '').strip()
        text2 = request.form.get('text2', '').strip()
        files = request.files.getlist('images')

        if len(files) < 2: return {"success": False, "message": "Cần ít nhất 2 ảnh"}

        cac_anh = [Image.open(f.stream).convert("RGB") for f in files]
        chieu_rong, chieu_cao = zip(*(anh.size for anh in cac_anh))
        
        max_rong = max(chieu_rong)
        tong_cao = sum(chieu_cao)
        
        anh_moi = Image.new('RGB', (max_rong, tong_cao), color=(0,0,0))
        toa_do_y = 0
        for anh in cac_anh:
            anh_moi.paste(anh, (0, toa_do_y))
            toa_do_y += anh.size[1]

        def tao_anh_chu(text, max_rong):
            if not text: return None
            font_size = int(max_rong * 0.045)
            try: font = ImageFont.truetype("arialbd.ttf", font_size)
            except: font = ImageFont.load_default()
            
            temp_img = Image.new("RGBA", (1, 1))
            temp_draw = ImageDraw.Draw(temp_img)
            bbox = temp_draw.textbbox((0, 0), text, font=font)
            padding_x, padding_y = int(font_size * 0.8), int(font_size * 0.5)
            wm_w = (bbox[2] - bbox[0]) + padding_x * 2
            wm_h = (bbox[3] - bbox[1]) + padding_y * 2
            wm_img = Image.new("RGBA", (wm_w, wm_h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(wm_img)
            draw.rounded_rectangle([0, 0, wm_w, wm_h], radius=int(font_size * 0.4), fill="#0092fa")
            draw.text((padding_x, padding_y - int(font_size * 0.1)), text, fill="white", font=font)
            return wm_img

        wm1 = tao_anh_chu(text1, max_rong)
        wm2 = tao_anh_chu(text2, max_rong)

        if wm1: anh_moi.paste(wm1, (int(max_rong * 0.04), cac_anh[0].size[1] - int(cac_anh[0].size[1] * 0.3)), mask=wm1)
        if wm2: anh_moi.paste(wm2, (int(max_rong * 0.04), tong_cao - cac_anh[-1].size[1] + int(cac_anh[-1].size[1] * 0.1)), mask=wm2)

        img_byte_arr = io.BytesIO()
        anh_moi.save(img_byte_arr, format='JPEG', quality=90)
        img_byte_arr.seek(0)

        if chat_id and chat_id != "0": bot.send_photo(chat_id, img_byte_arr, caption="✅ Ảnh của bạn đã ghép xong!")
        return {"success": True, "message": "Hoàn tất"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    markup = InlineKeyboardMarkup()
    btn = InlineKeyboardButton("🎨 Mở Tool Ghép Ảnh", web_app=WebAppInfo(url=WEB_URL))
    markup.add(btn)
    bot.send_message(message.chat.id, "Chào mừng bạn đến với Bot Ghép Ảnh FC Mobile!\n\nHãy nhấn vào nút bên dưới để mở Mini App nhé.", reply_markup=markup)

if __name__ == '__main__':
    bot_thread = threading.Thread(target=bot.infinity_polling)
    bot_thread.daemon = True
    bot_thread.start()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)