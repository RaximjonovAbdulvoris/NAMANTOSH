# Regionlar bo'yicha ariza boshqaruvi

Mavjud ariza taqsimlash, region tanlash, Brend/Spectre va izoh yozishmalarining
asosiy oqimi saqlanadi. Asosiy haydovchi arizasida Tayyor, Izoh berish,
Chala rasm, Boshqa park va Jarayonda tugmalari bor.

`.env.queues.example` dagi to'rtta manzilni serverdagi mavjud EnvironmentFile
ichiga kiriting. Har bir region uchun alohida Chala rasm va Boshqa park
guruhlari kerak. Arxiv manzillari avvalgidek: Namangan uchun ARCHIVE_GROUP,
Toshkent uchun TASHKENT_ARCHIVE_GROUP. Mavjud bot_routes.json ichidagi
sozlama environment qiymatidan ustun turadi.

Maxsus guruhda Tayyor, O'chirish, Jarayonda tugmalari bor. O'chirish avval
"Arizani barcha rasmlari bilan o'chirishni tasdiqlaysizmi?" deb so'raydi.
Ha, o'chirish yoki Bekor qilish tugmasini o'chirishni boshlagan operator
bosadi. Bekor qilish avvalgi tugmalar va Jarayonda rangini qaytaradi.
Tasdiqsiz hech narsa o'chirilmaydi. O'chirish arxivga yubormaydi.

Chala rasm / Boshqa park arizani saqlangan regionning guruhiga barcha
rasmlar, albomlar va ma'lumotlar bilan ko'chiradi. Jarayonda yangi guruhda
qizildan boshlanadi. To'liq nusxa tasdiqlangandan keyin eski xabarlar
o'chiriladi. Qisman nusxa yoki xato bo'lsa, asl ariza saqlanadi. Eski
xabarlarni o'chirish huquqi bo'lmasa, yozuv saqlanadi; huquq berilgach,
tugmani qayta bosish o'chirishni davom ettiradi, yangi nusxa yubormaydi.
Tayyor har ikki maxsus guruhdan o'z regionining arxiviga tugmalarsiz yuboradi.

Bot barcha ishchi guruhlarda administrator va xabarlarni o'chirish huquqiga
ega bo'lsin. PERSIST_DIR doimiy, yozish mumkin bo'lgan diskda bo'lsin;
bitta bot tokeni uchun bitta process ishlating. Telegram juda eski
xabarlarni o'chirishni cheklashi mumkin. Tarmoq uzilishi yoki process
nusxa yuborish paytida to'xtashi manzil guruhida qo'lda tozalashni talab
qiladigan nusxa qoldirishi mumkin.

Yangi tugmalar yangi arizalarda ko'rinadi. Saqlangan eski arizaning
Jarayonda tugmasi bosilganda uning klaviaturasi yangilanadi. Botni
qayta ishga tushirish barcha eski xabarlarga yangi tugmalarni avtomatik
qo'shmaydi. Eski arizalarning saqlangan holatini o'chirmang.

Tekshirish: `python -m unittest discover -s tests -v`.
Avval ikkala regionda sinov arizalari bilan ikkala maxsus guruhga
ko'chirish, Jarayonda, tasdiqlash/bekor qilish va arxivlashni jonli tekshiring.
