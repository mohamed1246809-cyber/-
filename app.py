from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import yt_dlp
import requests
import urllib.parse

app = Flask(__name__)
# السماح لجميع الاتصالات لمنع خطأ Failed to fetch
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/api/analyze', methods=['POST'])
def analyze_video():
    try:
        data = request.get_json(force=True, silent=True) or {}
        video_url = data.get('url', '').strip()

        if not video_url:
            return jsonify({'error': 'برجاء أدخل رابط صحيح'}), 400

        # إعدادات سرعة واستجابة سريعة جداً
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extract_flat': 'in_playlist',
            'playlistend': 30,
            'check_formats': False,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            if not info:
                return jsonify({'error': 'لم نتمكن من جلب بيانات لهذا الرابط'}), 400

            # 1. حالة قائمة التشغيل (Playlist)
            if info.get('_type') == 'playlist' or 'entries' in info:
                playlist_title = info.get('title') or 'قائمة تشغيل'
                raw_entries = info.get('entries') or []
                
                videos_list = []
                for idx, entry in enumerate(raw_entries, 1):
                    if not entry or not isinstance(entry, dict):
                        continue
                    v_id = entry.get('id', '')
                    v_url = entry.get('url') or entry.get('webpage_url') or f"https://www.youtube.com/watch?v={v_id}"
                    
                    videos_list.append({
                        'index': idx,
                        'id': v_id,
                        'title': entry.get('title') or f'فيديو #{idx}',
                        'url': v_url,
                        'thumbnail': f"https://i.ytimg.com/vi/{v_id}/hqdefault.jpg"
                    })

                return jsonify({
                    'is_playlist': True,
                    'title': playlist_title,
                    'count': len(videos_list),
                    'videos': videos_list,
                    'formats': []
                })

            # 2. حالة الفيديو المنفرد
            formats_raw = info.get('formats') or []
            formats_list = []
            seen_resolutions = set()

            for f in formats_raw:
                if not isinstance(f, dict):
                    continue
                
                f_url = f.get('url')
                if not f_url:
                    continue

                height = f.get('height')
                vcodec = f.get('vcodec', 'none')
                acodec = f.get('acodec', 'none')

                if height and height not in seen_resolutions:
                    seen_resolutions.add(height)
                    formats_list.append({
                        'quality': f"{height}p",
                        'ext': f.get('ext', 'mp4'),
                        'url': f_url
                    })
                elif vcodec == 'none' and acodec != 'none' and 'صوت فقط (M4A)' not in [x['quality'] for x in formats_list]:
                    formats_list.append({
                        'quality': 'صوت فقط (M4A)',
                        'ext': 'm4a',
                        'url': f_url
                    })

            if not formats_list:
                for f in formats_raw:
                    if f.get('url'):
                        formats_list.append({
                            'quality': f.get('format_note') or 'جودة تلقائية',
                            'ext': f.get('ext', 'mp4'),
                            'url': f['url']
                        })

            formats_list.sort(
                key=lambda x: int(x['quality'].replace('p', '')) if x['quality'].replace('p', '').isdigit() else 0, 
                reverse=True
            )

            return jsonify({
                'is_playlist': False,
                'title': info.get('title') or 'فيديو بدون عنوان',
                'thumbnail': info.get('thumbnail') or f"https://i.ytimg.com/vi/{info.get('id', '')}/hqdefault.jpg",
                'formats': formats_list,
                'videos': []
            })

    except Exception as e:
        return jsonify({'error': f"خطأ في التحليل: {str(e)}"}), 500

if __name__ == '__main__':
    print("السيرفر يعمل الآن بنجاح على: http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True)