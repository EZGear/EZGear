# Desktop Pet — ekranda yuradigan personajlar

Kompyuter ekranida (barcha oynalar ustida) anime personajlar yuradi:
Eren va Mikasa (Attack on Titan, High School versiyasi) — yoki istalgan boshqa
personaj, agar uning rasmlari bo'lsa.

## Nima qila oladi
- Ekran tepasidan tushib keladi, taskbar ustida yuradi, yuguradi, o'tiradi, yotadi, emaklaydi, sakraydi
- Ekran chetidagi devorga tirmashib chiqadi, shiftda osilib yuradi, keyin qo'yib yuborib tushadi
- **Mikasa ko'pincha Erenning orqasidan ergashib yuradi**
- Sichqoncha bilan ushlab sudrash va **otib yuborish** mumkin
- O'ng tugma bosilsa menyu chiqadi: yana Eren/Mikasa qo'shish, o'tirg'izish, yopish, chiqish

## 1. Rasmlarni joylash
Dastur standart **Shimeji** rasm formatini ishlatadi (`shime1.png` ... `shime46.png`).
Sizdagi Attack on Titan High School shimeji to'plamidan rasmlarni ko'chiring:

```
desktop-pet/
  img/
    Eren/    shime1.png, shime2.png, ... shime46.png
    Mikasa/  shime1.png, shime2.png, ... shime46.png
```

Rasmlar qo'yilmasa, dastur vaqtinchalik oddiy shakllarni ko'rsatadi, ya'ni
ishlashini darhol tekshirib ko'rsa bo'ladi.
`img/` ichiga yangi papka qo'shsangiz (masalan `img/Armin`), u ham avtomatik chiqadi.

## 2. Ishga tushirish (Windows)
**A variant — Python bilan:**
1. https://www.python.org/downloads/ dan Python o'rnating ("Add python.exe to PATH" belgisini qo'ying).
2. `run.bat` faylini ikki marta bosing.

**B variant — tayyor .exe:**
GitHub'da repozitoriy → **Actions** → "Desktop Pet (Windows .exe)" → oxirgi ishga tushirish →
**DesktopPet-windows** arxivini yuklab oling. Ichidagi `img` papkasiga rasmlarni qo'ying va
`DesktopPet.exe` ni ishga tushiring. Yoki o'zingiz `build_exe.bat` bilan yig'ishingiz mumkin.

## 3. Sozlamalar — `settings.json`
| Kalit | Ma'nosi |
|---|---|
| `scale` | O'lcham (masalan `0.7` — kichikroq, `1.5` — kattaroq) |
| `characters` | Boshida nechtadan chiqishi: `{"Eren": 1, "Mikasa": 1}` |
| `follow` | Kim kimning orqasidan yuradi: `{"Mikasa": "Eren"}` |
| `max_pets` | Ekrandagi eng ko'p personajlar soni |

## Chiqish
Istalgan personajni o'ng tugma bilan bosing → **Chiqish (hammasini yopish)**.

> Eslatma: to'liq shaffoflik Windows'da ishlaydi. macOS'da ham ishlaydi, Linux'da esa
> personaj atrofida rangli fon ko'rinishi mumkin.
