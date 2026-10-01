# yiming 異名 (Dị danh)

**Làm hiện ra những tên ngoại tộc bị chữ Hán che khuất trong sử sách Trung Quốc.**

[English](README.md) · [简体中文](README.zh-CN.md) · [한국어](README.ko.md) · [日本語](README.ja.md) · [Tiếng Việt](README.vi.md)

![Phía trên 禄山 hiện dạng gốc tiếng Sogdia Roxšan; khung chú thích giải thích tên và họ 安](docs/img/anlushan.png)

## Vì sao có công cụ này

Sử sách Trung Quốc ghi tên người, tên dân tộc và địa danh nước ngoài bằng chữ Hán. Vì vậy, dáng vẻ ban đầu của các tên đó bị che khuất.

- **Tên gốc biến mất.** Tên "禄山" của An Lộc Sơn (安禄山) vốn là tiếng Sogdia *Roxšan* ("sáng"), cùng gốc với tên Hy Lạp *Roxana*. Đọc theo tiếng Hán hiện đại *Lùshān* thì không nhận ra được gì. Đọc theo âm đời Đường *luk-ʂɛn* thì thấy ngay.
- **Một tên, nhiều cách viết.** Người Oirat được ghi là 斡亦剌, 瓦剌, 厄鲁特, 卫拉特 tùy thời kỳ. Đế quốc Ottoman là 鲁迷 (Rūm, "La Mã") thời Minh, 控噶尔 thời Thanh, rồi 土耳其.
- **Người đời sau làm rối thêm.** Khi biên soạn *Tứ khố toàn thư* (四库全书), vua Càn Long cho sửa lại gần như mọi tên ngoại tộc trong sử Liêu, Kim, Nguyên (伯颜→巴延, 脱脱→托克托, 拔都→巴图). Mà phần lớn văn bản điện tử trên mạng lại là bản Tứ khố.

yiming đọc một bộ sử và **viết dạng nguyên ngữ phía trên mỗi tên ngoại tộc**, tô màu theo ngữ hệ. Nó hiển thị các cách viết khác nhau của cùng một tên theo một dạng thống nhất, và khôi phục những tên bị đời Càn Long sửa. **Văn bản gốc không bao giờ bị thay đổi:** cách viết mà đoạn văn thực sự dùng luôn được giữ bên cạnh.

## Hiện nay làm được gì

- **Giao diện đọc.** Mỗi tên ngoại tộc được đánh dấu như sau:
  - phía trên: dạng gốc (*Roxšan*, *Bayan*, *Rūm*);
  - màu: ngữ hệ (12 ngữ hệ);
  - gạch dưới: mức độ chắc chắn của việc xác định.
  
  Rê chuột lên tên để xem ngôn ngữ, nghĩa, nguồn, các cách viết khác và các tên khác của cùng một đối tượng.
- **Âm đọc theo thời đại.** Tên được so sánh theo cách đọc của thời kỳ nó được ghi:
  - Hán–Đường: Trung cổ âm (vận thư *Thiết vận* 切韵);
  - Tống–Minh: âm quan thoại cận cổ (gần đúng);
  - Thanh: âm quan thoại thời Thanh (gần đúng).
  
  Các thói quen phiên âm quen thuộc cũng được đưa vào. Ví dụ, đời Đường dùng vần cuối *-t* để ghi *-r/-l* của tiếng nước ngoài (阙 = *kül*).
- **Không chỉ Nhị thập tứ sử.** Công cụ tải văn bản từ kho Kanripo (khoảng 9.000 đầu sách) và tự chọn hệ âm đọc phù hợp với thời đại của sách.
- **Khôi phục bản Tứ khố.**
  - Dùng *Khâm định Liêu Kim Nguyên tam sử quốc ngữ giải* (钦定辽金元三史国语解), khoảng 7.400 cặp.
  - So sánh từng chữ giữa hai bản của cùng một bộ sách (khoảng 3.600 cặp trong phần bản kỷ của *Nguyên sử*).
  - Khi một cách viết đời Càn Long thay cho nhiều tên cũ, công cụ không đoán mà đánh dấu và liệt kê các khả năng.
- **Trang web cho cả bộ sách.** Biến một bộ sách thành một trang web nhỏ gồm:
  - mỗi quyển một trang;
  - mục lục với thanh màu thể hiện lượng tên ngoại tộc và ngữ hệ của từng quyển;
  - bảng tra tên liên kết mỗi tên tới các quyển có nó.
- **Công cụ khám phá.**
  - Lập danh sách mọi tên phiên âm trong một bộ sách.
  - Tìm các tên đọc gần giống nhau nhưng viết khác nhau (những trường hợp có thể là "một người hai truyện").
  - Tùy chọn: nhờ LLM đề xuất dạng gốc cho các tên chưa biết. Chỉ giữ đề xuất khớp với âm đọc của thời đại.
- **Độ chính xác đo được.** Lệnh đánh giá cho biết bao nhiêu xác định đúng và sai vượt qua bước kiểm tra âm (xem [Độ chính xác](#độ-chính-xác)).

## Bắt đầu nhanh

### 1. Cài đặt

Cần Python 3.8 trở lên, không cần thư viện ngoài.

```bash
git clone https://github.com/<tài-khoản>/yiming.git
cd yiming
python yiming.py setup          # tạo bảng dị thể chữ (cần mạng một lần)
```

Tùy chọn:

| Gói | Dùng cho |
|---|---|
| `pypinyin` | chữ không có trong vận thư |
| `anthropic` | lệnh `propose` |
| `opencc` | tạo lại `mc_table.json` |

### 2. Chuẩn bị văn bản

Dùng một trong hai nguồn, hoặc cả hai.

```bash
# (a) Nhị thập tứ sử từ hunterhug/china-history (khoảng 250MB)
git clone --depth 1 https://github.com/hunterhug/china-history.git corpus

# (b) Bất kỳ sách nào trên Kanripo, theo tên hoặc mã KR
python yiming.py fetch 资治通鉴 --corpus corpus --juan 214
python yiming.py fetch 大唐西域记 --corpus corpus
```

### 3. Đọc

```bash
# một quyển -> một trang
python yiming.py read corpus/旧唐书/列传/第一百五十章-卷一百五十-原文.html -o anlushan.html

# cả bộ sách -> một trang web có thể duyệt (tên đầu ra không có .html)
python yiming.py read corpus/元史 -o yuan_site
```

Mở tệp HTML bằng trình duyệt. Thư mục [`samples/`](samples/) có sẵn các ví dụ.

## Cách đọc trang

**Phía trên tên:** dạng nguyên ngữ (in nghiêng). Nếu chỉ biết ngôn ngữ mà chưa biết dạng gốc thì hiện ‹Khitan›.

**Màu = ngữ hệ**

| Ngữ hệ | Ví dụ |
|---|---|
| Nhóm Iran (Sogdia, Bactria, Parthia, Saka Khotan, Ba Tư) | 禄山 *Roxšan*, 粟特 *Soγd*, 安息 *Aršak*, 哈烈 *Herāt* |
| Turk | 突厥 *Türk*, 可汗 *qaγan*, 回纥 *Uyγur*, 鲁迷 *Rūm* |
| Mông Cổ | 帖木儿 *Temür*, 拔都 *ba'atur*, 斡罗思 *Orus* |
| Cận Mông Cổ (Khiết Đan, Tiên Ti) | 契丹 *Kitan*, 拓跋 *Tabγač*, 耶律 |
| Tungus (Nữ Chân, Mãn) | 女真 *Jürchen*, 勃极烈 *bogile*, 贝勒 *beile* |
| Tạng | 喇嘛 *bla ma*, 拉萨 *Lha sa* |
| Nhóm Ấn (Phạn, Pali) | 佛陀 *Buddha*, 阿罗汉 *arhat*, 鸠摩罗什 |
| Dravida | 古里 *Kōḻikkōṭ* (Calicut), 柯枝 *Kochi* |
| Semit (Syria, Ả Rập) | 移鼠 *Išoʿ* (Giê-su), 默德那 *al-Madīna* |
| Nam Đảo | 满剌加 *Melaka*, 爪哇 *Jawa*, 吕宋 *Luzon* |
| Ngôn ngữ châu Âu | 和兰 *Holland*, 利玛窦 *Matteo Ricci* |
| Khác / chưa rõ | 勃律 *Bolor*; màu xám nghĩa là chưa rõ dạng gốc |

**Gạch dưới = mức độ chắc chắn**

| Kiểu gạch | Ý nghĩa |
|---|---|
| liền | Xác định từ bảng từ vựng đã biên soạn, có nguồn |
| đứt | Đề xuất của LLM đã qua bước kiểm tra âm; nguồn chưa được kiểm chứng |
| chấm xám | Trông như phiên âm, nhưng chưa rõ dạng gốc |
| lượn sóng xám | Một cách viết đời Càn Long thay cho hơn một tên cũ; rê chuột để xem các khả năng |

**Chữ xám nhỏ sau tên:** cách viết mà đoạn văn thực sự dùng. Nó xuất hiện khi tên được hiển thị theo dạng thống nhất.

**Khung chú thích** (rê chuột, hoặc phím Tab): ngôn ngữ, nghĩa, nguồn, các cách viết khác, các tên khác của cùng một đối tượng (鲁迷 ↔ 控噶尔 ↔ 土耳其). Trong sử đời Đường, nếu trước tên có họ 安, 康, 石, 米, 何, 史 hoặc 曹, khung chú thích còn cho biết thành phố Sogdia mà họ đó chỉ tới.

## Chi tiết các chức năng

### Âm đọc theo thời đại và so sánh âm

Vị trí âm vị học trong *Thiết vận* của từng chữ lấy từ dữ liệu `qieyun` của nk2028 (CC0). Mỗi tên được chuyển thành chuỗi loại âm: âm đầu, nguyên âm, âm cuối. Ví dụ 禄山 thành `LuK SaN`, *Roxšan* thành `RuH SaN`.

Hai tên, hoặc một tên và dạng gốc viết bằng chữ Latinh, được so sánh bằng khoảng cách chỉnh sửa có trọng số. Các thói quen phiên âm quen thuộc chỉ bị trừ ít điểm:

- *l* ↔ *r*;
- *k* ↔ *x/h*;
- đời Đường dùng *-t* cho *-r/-l*;
- phương ngữ Tây Bắc mất tính mũi của phụ âm đầu, nên 默 có thể ghi *b-* (默啜 = *Bäg Čor*);
- phụ âm cuối bị lược (颉利 = *Illig*).

| Hệ | Dùng cho | Quy tắc chính |
|---|---|---|
| `mc` | Sử liệu Hán–Đường–Ngũ Đại | Thanh mẫu *Thiết vận*; giữ âm cuối *-p -t -k -m -n -ŋ* |
| `om` | Tống, Liêu, Kim, Nguyên, Minh | Mất âm cuối nhập thanh; mẫu 疑 thành phụ âm đầu zero; mẫu 日 ≈ *r* |
| `qm` | Thanh | Như `om`, thêm *-m* nhập vào *-n*; vẫn giữ phân biệt tiêm âm/đoàn âm (như cách người đời Thanh phiên tiếng Mãn) |

Hệ âm được chọn theo **thời đại của sử liệu**, không theo thời đại người biên soạn. *Minh sử* được người Thanh soạn từ tư liệu đời Minh, nên dùng `om`. Công cụ xem bảng tên sách trước, rồi đến triều đại ghi lại lúc tải sách. Cũng có thể chỉ định bằng `--scheme`.

**Bộ lọc thời đại:** một mục từ không bao giờ được khớp trong sách cổ hơn dạng viết sớm nhất của nó. Vì thế 古里 là Calicut trong văn bản đời Minh, nhưng không phải trong *Cựu Đường thư*.

### Tên: bảng từ vựng, cách viết, thực thể

| Bảng | Nội dung |
|---|---|
| `lexicon.tsv` | 123 mục đã biên soạn: dạng gốc, ngôn ngữ, ngữ hệ, nghĩa, các dạng chữ Hán, nguồn |
| `equivalence.tsv` | Các cách viết khác nhau của cùng một tên, hiển thị theo một dạng thống nhất |
| cột `entity` | Các **tên** khác nhau của cùng một đối tượng; được liên kết, không gộp |

Khớp được cả giản thể lẫn phồn thể. Khoảng 21.000 dị thể chữ (竒 → 奇) được quy về chính thể.

### Sách khác: Kanripo

```bash
python yiming.py fetch KR2a0036 --corpus corpus --juan 1-47 --name 元史_四库
```

Văn bản được làm sạch thành `corpus/<tên-sách>/NNN.txt`, triều đại người soạn được lưu trong `meta.json`. Bản Tứ khố không có dấu câu, nên đoạn văn được chia theo trang.

### Bản Tứ khố: khôi phục tên bị đời Càn Long sửa

1. `guoyujie` trích *Tam sử quốc ngữ giải* thành các cặp "cách viết Càn Long → cách viết cũ". Những "nghĩa tiếng Mãn, tiếng Mông Cổ" mà Càn Long gán cho các tên thì **không dùng**, vì nhiều nghĩa là gán ghép.
2. `align A B` so sánh từng quyển giữa hai bản của cùng một bộ sách và thu lại mọi đoạn ngắn khác nhau trông giống phiên âm. Cách viết Tứ khố phải không xuất hiện trong bản cũ.
3. Khi đọc sách tải từ Kanripo, các tên bị sửa được tự động khôi phục, cách viết Tứ khố vẫn giữ bằng chữ xám nhỏ. Nếu một cách viết thay cho nhiều tên cũ (俄罗斯 thay cho cả 斡罗思 *Orus* lẫn 兀鲁思 *ulus*), tên được giữ nguyên với gạch lượn sóng, và khung chú thích liệt kê các khả năng cùng số lần.
4. Văn bản đời Thanh vốn viết theo những cách đó, nên **không khôi phục**.

![Nguyên sử bản Tứ khố: 巴图 được khôi phục thành 拔都 (ba'atur), cách viết Tứ khố giữ bằng màu xám](docs/img/siku.png)

### Trang web cho cả bộ sách

`read THƯ-MỤC-SÁCH -o THƯ-MỤC-RA` tạo:

- `index.html`: mục lục, mỗi quyển một thanh màu theo ngữ hệ;
- mỗi quyển một trang, có liên kết trước/sau;
- `names.html`: mọi tên, nhóm theo ngữ hệ, kèm số lần và liên kết tới các quyển.

201 quyển *Cựu Đường thư* mất khoảng 6 giây.

### Công cụ khám phá

| Lệnh | Chức năng |
|---|---|
| `scan` | Bảng mọi tên phiên âm trong một bộ sách: số lần, trạng thái, dạng gốc, ngữ hệ, ngữ cảnh đầu tiên |
| `twins` | Các tên đọc gần giống mà viết khác (ví dụ 萧得里底 / 萧迭里得). Đây là danh sách cần xem xét, không phải kết luận |
| `propose` (thử nghiệm) | Gửi các tên chưa biết, kèm âm đọc thời đại và một dòng ngữ cảnh, cho LLM. Những chuỗi bị coi là từ Hán thông thường sẽ bị loại. Dạng gốc được đề xuất chỉ được giữ nếu khớp âm (≥ 0.60) và hiển thị bằng gạch đứt. Câu trả lời được lưu đệm. **Hiện mới chỉ thử bằng câu trả lời giả lập.** |

### Độ chính xác

Kết quả của `python yiming.py eval gold_pairs.tsv --corpus corpus` (xem `samples/eval.txt`).

**Dạng chữ Hán so với dạng gốc:** 166 cặp đúng từ bảng từ vựng, so với 19.920 cặp sai.

| Ngưỡng | Xác định đúng được giữ | Xác định sai lọt vào |
|---|---|---|
| 0.55 | 78% | 4.0% |
| **0.60** (mặc định của `propose`) | 72% | 2.2% |
| 0.70 | 54% | 0.75% |

**Cách viết so với cách viết:** 19 cặp dị bản đã biết, so với 20.000 cặp tên ngẫu nhiên. Ở ngưỡng 0.80, độ phủ 79%, tỉ lệ báo nhầm 0.17% mỗi cặp.

Khớp âm chỉ là bộ lọc, không phải bằng chứng.

## Danh sách lệnh

| Lệnh | Mục đích |
|---|---|
| `read TỆP-HOẶC-THƯ-MỤC -o ĐẦU-RA` | Giao diện đọc. Đầu ra `.html` cho một trang, tên thư mục cho trang web cả bộ sách. Tùy chọn: `--display latin`, `--known-only`, `--unknown-mean`, `--scheme`, `--siku on/off` |
| `find TỪ --corpus THƯ-MỤC` | Những tệp có chứa từ đó |
| `fetch TÊN-HOẶC-MÃ --corpus THƯ-MỤC` | Tải từ Kanripo; `--juan 1-10`, `--name` |
| `setup` | Tạo `variants.json` (bảng dị thể chữ) |
| `guoyujie` | Trích các tên bị sửa từ *Tam sử quốc ngữ giải* |
| `align A B -o TỆP` | So sánh hai bản, thu các tên bị đổi |
| `scan`, `twins`, `propose` | Công cụ khám phá (xem trên) |
| `key TÊN`, `match A B` | Xem âm cổ; so sánh hai tên (hoặc tên với dạng gốc) |
| `train --corpus THƯ-MỤC` | Học lại các chữ thường dùng để phiên âm |
| `eval gold_pairs.tsv` | Báo cáo độ chính xác |

Tài liệu chi tiết bằng tiếng Trung nằm trong [`docs/`](docs/) (bản một trang: `docs/指南.html`).

## Hạn chế

- **Ngôn ngữ của tên là bằng chứng về bối cảnh văn hóa, không phải bằng chứng về huyết thống.** Bằng chứng mạnh khi khớp với các manh mối khác (họ, quê quán, sử gọi là "胡"). Bằng chứng yếu ở những thời mà tên ngoại tộc là mốt, như người Hán đời Nguyên mang tên Mông Cổ, hay tăng sĩ mang pháp danh tiếng Phạn.
- **Độ bao phủ phụ thuộc vào bảng từ vựng.** Trong *Nguyên sử* phát hiện được khoảng 930 tên phiên âm, nhưng bảng từ vựng đã biên soạn chỉ có khoảng 50. Phần còn lại hiện màu xám cho đến khi `propose` hoặc người dùng bổ sung.
- **Việc phát hiện dựa trên thống kê.** Trong văn bản đời Đường, một số từ Hán (như 补阙) bị nhận nhầm.
- **Khôi phục bản Tứ khố chưa hoàn hảo.** Có tên bị sửa mà bị bỏ sót, và đôi khi bước so sánh kéo lẫn chữ bên cạnh vào tên.
- **`propose` chưa được thử với câu trả lời thật của LLM.**
- **Nhiều nguồn trong bảng từ vựng chỉ ghi "standard" (thuyết thông dụng).** Cần dần thay bằng tài liệu cụ thể.
- ***Thanh sử cảo* có trong thư mục của Kanripo, nhưng chưa công bố văn bản.**

## Mở rộng yiming ra ngoài phạm vi hiện tại

### Phạm vi hiện tại

- **Văn bản:** Nhị thập tứ sử (hunterhug) và các sách trên Kanripo, tức sử liệu chữ Hán từ Hán đến Thanh.
- **Âm đọc:** ba hệ `mc`, `om`, `qm`, đều suy từ *Thiết vận*.
- **Tên:** chủ yếu là tên Nội Á, Nam Á, Tây Á, cùng một số tên vùng biển và châu Âu, chia thành 12 ngữ hệ.

### Danh sách việc cần làm khi mở rộng

1. **Văn bản.** Đặt văn bản thuần vào `corpus/<tên-sách>/*.txt`, mỗi đoạn một dòng (`.html` cũng được). Với nguồn mới, hãy viết một bộ chuyển đổi nhỏ; tham khảo `corpora.clean_mandoku`.
2. **Thời đại.** Thêm tên sách vào `BOOK_SCHEME` trong `origin.py`, hoặc ghi `"scheme": "mc"` vào `meta.json` của sách.
3. **Âm đọc.** Nếu không hệ nào trong `mc`, `om`, `qm` phù hợp, hãy thêm hệ mới:
   - Mở rộng `syllable()` (quy tắc dựa trên *Thiết vận*) hoặc `Phon.char_sylls()` (dữ liệu âm đọc khác) trong `yiming.py`, để mỗi chữ trả về (loại âm đầu, loại âm cuối, loại nguyên âm).
   - Thêm tên hệ vào lựa chọn dòng lệnh và vào `ERA` trong `origin.py`.
   - Nếu ngôn ngữ mới có những tương ứng âm điển hình, thêm chúng vào `SUB` và `INDEL` trong `yiming.py`.
4. **Tên.** Thêm mục vào `lexicon.tsv` kèm nguồn thật. Ngữ hệ mới cần thêm vào `FAMILIES` và cho một màu trong phần CSS của `origin.py`.
5. **Cách viết.** Đưa các dị bản của cùng một tên vào `equivalence.tsv`. Nếu có bản nào sửa tên như bản Tứ khố, hãy dùng `align` để so với bản chưa sửa.
6. **Phát hiện.** Chạy `train --corpus THƯ-MỤC` trên văn bản mới. Nếu truyền thống đó có bộ chữ phiên âm riêng, thêm chúng vào `SEED_CHARS` trong `origin.py`.
7. **Kiểm tra độ chính xác.** Đưa các cặp tương ứng đã được xác nhận của lĩnh vực mới vào `gold_pairs.tsv` rồi chạy `eval`. Chỉ tin ngưỡng mà bạn đã tự đo.
8. **Đề xuất của LLM (tùy chọn).** Sửa `PROMPT` trong `origin.py` để mô tả lĩnh vực mới.

### Hướng dẫn theo từng trường hợp

| Phạm vi | Cần thay đổi gì |
|---|---|
| **Sử Hàn Quốc viết bằng chữ Hán** (Tam quốc sử ký, Cao Ly sử, Triều Tiên vương triều thực lục) | Tên Nữ Chân, Mông Cổ, Nhật Bản thường do văn nhân Triều Tiên phiên âm. Thêm hệ âm Hán-Hàn (trường `kHangul` trong cơ sở dữ liệu Unihan của Unicode cho âm đọc; âm cuối *-l* của Hán-Hàn tương ứng với *-t* Trung cổ). Thêm các ngữ hệ Triều Tiên, Nhật Bản. |
| **Sử Nhật Bản viết bằng chữ Hán** (Nhật Bản thư kỷ, Tục Nhật Bản kỷ…) | Tên Triều Tiên, Ainu được ghi âm bằng chữ Hán, thường gần với lối man'yōgana. Thêm hệ âm Hán-Nhật (Unihan `kJapaneseOn`; *-tsu/-chi* ↔ *-t*, *-ku/-ki* ↔ *-k*). |
| **Sử Việt Nam viết bằng chữ Hán** (*Đại Việt sử ký toàn thư*, *Khâm định Việt sử thông giám cương mục*) | Tên Chăm, Khmer, Thái. Thêm hệ âm Hán-Việt (Unihan `kVietnamese`; giữ âm cuối *-t, -c, -p*), cùng các ngữ hệ Nam Á, Tai–Kadai. |
| **Kinh Phật** (CBETA) | Viết bộ chuyển đổi cho TEI XML. Các phiên âm sớm thời Đông Hán (như 浮屠) có trước *Thiết vận*: thêm hệ Thượng cổ âm hoặc âm Hậu Hán theo một bản phục nguyên đã công bố. |
| **Thời kỳ sớm hơn** (Hung Nô, Tây Vực trong *Sử ký*, *Hán thư*) | Như trên, cần hệ âm trước *Thiết vận*. Vì hiểu biết về ngôn ngữ gốc còn ít, độ chính xác sẽ thấp hơn. |
| **Văn bản cuối Thanh và thời Dân Quốc** | Tên phương Tây được phiên theo quan thoại, hoặc theo tiếng Quảng Đông, tiếng Mân Nam. Thêm hệ dựa trên pinyin, và hệ tiếng Quảng Đông (Unihan `kCantonese`) cho văn bản miền Nam. |
| **Các bản khác từng bị sửa tên** | Bất kỳ hai bản nào cũng có thể so sánh bằng `align`. |

## Nguồn dữ liệu và giấy phép

Xem [DATA_SOURCES.md](DATA_SOURCES.md).

- Mã nguồn theo giấy phép MIT.
- `mc_table.json` lấy từ dữ liệu qieyun của nk2028 (CC0).
- Các ví dụ và bảng tên Tứ khố lấy từ văn bản Kanripo; hãy kiểm tra điều kiện của Kanripo trước khi tái sử dụng.
- `variants.json` được tạo tại máy người dùng từ bảng dị thể cjkvi, không đưa vào kho mã.
- Kho mã này không phân phối lại văn bản của hunterhug.

## Đóng góp

Thấy xác định sai hoặc thiếu? Hãy cho biết ba điều:

1. tên sách và quyển;
2. câu văn đó;
3. điều bạn cho là đúng, **kèm nguồn**.

Có ba điều này thì ai cũng có thể kiểm chứng và sửa. Rất hoan nghênh các đề xuất sửa `lexicon.tsv` có trích dẫn thật.

## Lời cảm ơn

- nk2028 (dữ liệu qieyun);
- Kanripo / 漢籍リポジトリ (văn bản);
- cjkvi (bảng dị thể);
- hunterhug/china-history (kho Nhị thập tứ sử);
- các nghiên cứu được trích trong `lexicon.tsv`: Pulleyblank, de la Vaissière, Shimunek, và các học giả khảo chứng 鲁迷, 控噶尔.
