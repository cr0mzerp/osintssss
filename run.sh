# Lokal
pip install -r requirements.txt
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8901
# aç: http://127.0.0.1:8901

# Vercel deploy
# 1. Bu klasörü git repo yapıp pushla
# 2. vercel.com -> Add New Project -> repo'yu seç (framework: Other)
# 3. Deploy. API: /api/search?name=Ad+Soyad (max 60sn), arayüz: /
npx vercel --prod
