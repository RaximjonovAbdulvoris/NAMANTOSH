# TURON TAXI — yangi botni sozlash

Bot ikki hudud uchun: Toshkent va Namangan. Har birida haydovchi, Brend va
arxiv guruhlari mustaqil. Haydovchi arizasi operatorga rasm albomi va ma'lumot
xabarini yuboradi. Tugmalar: Tayyor, Izoh berish, Jarayonda. Brend arizasi
guruhga oddiy matn sifatida yuboriladi.

Yangi token va alohida doimiy `PERSIST_DIR` ishlating. Eski HUMO botining
`.env`, `bot_routes.json` yoki `bot_persistence.pkl` fayllarini ko'chirmang.
Telegram guruh IDlarini quyidagi muhit o'zgaruvchilari orqali kiriting:

- Namangan: `DRIVER_GROUP_1`, `DRIVER_GROUP_2`, `BRAND_GROUP`, `ARCHIVE_GROUP`.
- Toshkent: `TASHKENT_DRIVER_GROUP_1`, ixtiyoriy `TASHKENT_DRIVER_GROUP_2`,
  `TASHKENT_BRAND_GROUP`, `TASHKENT_ARCHIVE_GROUP`.

Aloqa matni tayyor bo'lganda `TURON_CONTACT_TASHKENT` va
`TURON_CONTACT_NAMANGAN` ga hududga mos matn kiriting. Hozir ular bo'sh
bo'lsa, bot eski parkning aloqa ma'lumotini ko'rsatmaydi.

`python -m bot.configure check --scope all` bilan Toshkent guruhlari va bot
huquqlarini tekshiring. Namangan guruhlari uchun ham botning administrator va
xabarlarni o'chirish huquqi borligini alohida tekshiring. Har ikkala hududdan
sinov arizasi yuborib, manzil va arxiv oqimini tasdiqlang.
