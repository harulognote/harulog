-- HaruLog Database Backup
-- Generated at: 2026-10-30 14:59:47
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- --------------------------------------------------------
-- Table structure for `app_admin_audit`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `app_admin_audit`;
CREATE TABLE `app_admin_audit` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `actor_id` bigint(20) NOT NULL,
  `target_id` bigint(20) NOT NULL,
  `action` varchar(40) NOT NULL,
  `details` text NOT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table structure for `app_members`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `app_members`;
CREATE TABLE `app_members` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `username` varchar(64) NOT NULL,
  `display_name` varchar(100) NOT NULL DEFAULT '',
  `password_hash` varchar(255) NOT NULL,
  `role` varchar(16) NOT NULL DEFAULT 'user',
  `status` varchar(16) NOT NULL DEFAULT 'pending',
  `auth_version` int(11) NOT NULL DEFAULT 1,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dumping data for table `app_members` (1 rows)
LOCK TABLES `app_members` WRITE;
INSERT INTO `app_members` (`id`, `username`, `display_name`, `password_hash`, `role`, `status`, `auth_version`, `created_at`, `updated_at`) VALUES
(1, 'bekyjung', 'bekyjung', 'scrypt:32768:8:1$K7lZiCXrzcgXn6Vb$33051df0c76cbc984abaca8c434a1821aca119cccdcd1c743fe98f6372ba25a97dc20c632e7e41b84b629e363115b23f99b5fd49c1f4f1c57aba262121279916', 'admin', 'active', 1, '2026-10-28 19:14:12', '2026-10-28 19:14:12');
UNLOCK TABLES;

-- --------------------------------------------------------
-- Table structure for `app_system`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `app_system`;
CREATE TABLE `app_system` (
  `name` varchar(64) NOT NULL,
  `value` varchar(255) NOT NULL,
  PRIMARY KEY (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dumping data for table `app_system` (1 rows)
LOCK TABLES `app_system` WRITE;
INSERT INTO `app_system` (`name`, `value`) VALUES
('ownership_v1', '1');
UNLOCK TABLES;

-- --------------------------------------------------------
-- Table structure for `daily_logs`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `daily_logs`;
CREATE TABLE `daily_logs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `content` text NOT NULL,
  `created_at` datetime NOT NULL,
  `file_path` varchar(255) DEFAULT NULL,
  `owner_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_daily_logs_owner` (`owner_id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dumping data for table `daily_logs` (4 rows)
LOCK TABLES `daily_logs` WRITE;
INSERT INTO `daily_logs` (`id`, `content`, `created_at`, `file_path`, `owner_id`) VALUES
(1, 'AI와함께종일프로그래밍', '2026-10-26 19:59:58', '/uploads/20261026_232309_3e44b409.jpg', 1),
(2, 'Openai 사용량 재지정 대기중 🤣', '2026-10-26 23:22:32', '/uploads/20261026_232232_e56a762f.jpg', 1),
(3, '오늘도 시~~작, 마깐둘루!!!', '2026-10-27 10:31:41', '/uploads/20261027_131936_3dba8eca.jpg', 1),
(4, '아침 댓바람부터 6인 회동 ~ 차차차 🥰\r\nLittle Frenchie JKT & 청해수산', '2026-10-29 15:22:12', '/uploads/20261029_152212_408135f7.jpg', 1);
UNLOCK TABLES;

-- --------------------------------------------------------
-- Table structure for `expense_invoices`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `expense_invoices`;
CREATE TABLE `expense_invoices` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `billing_month` char(7) NOT NULL,
  `invoice_number` varchar(100) NOT NULL,
  `property_name` varchar(150) NOT NULL,
  `unit_name` varchar(80) NOT NULL,
  `due_date` date DEFAULT NULL,
  `paid_date` date DEFAULT NULL,
  `paid` tinyint(4) NOT NULL DEFAULT 0,
  `items_json` longtext NOT NULL,
  `readings_json` text NOT NULL,
  `billed_total` decimal(18,2) NOT NULL,
  `memo` text NOT NULL,
  `photo_path` varchar(255) DEFAULT NULL,
  `ocr_text` longtext NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  `owner_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_expense_month` (`billing_month`,`id`),
  KEY `idx_expense_invoices_owner` (`owner_id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dumping data for table `expense_invoices` (10 rows)
LOCK TABLES `expense_invoices` WRITE;
INSERT INTO `expense_invoices` (`id`, `billing_month`, `invoice_number`, `property_name`, `unit_name`, `due_date`, `paid_date`, `paid`, `items_json`, `readings_json`, `billed_total`, `memo`, `photo_path`, `ocr_text`, `created_at`, `updated_at`, `owner_id`) VALUES
(1, '2026-10', '093/X/2026', 'APARTEMEN SLIPI', '1/18-C', '2026-10-15', NULL, 0, '[{"name": "전기 사용요금", "amount": "1097896.00"}, {"name": "공용설비비 (Utilitas)", "amount": "583000.00"}, {"name": "전기세금 (PBJT-TL)", "amount": "40342.00"}, {"name": "행정비", "amount": "6000.00"}, {"name": "수도 기본료", "amount": "30400.00"}]', '{"electricity": {"previous": "16537.00", "current": "17183.00", "usage": "646.00", "rate": "1699.53"}, "water": {"previous": "7234.00", "current": "7234.00", "rate": "21500.00"}, "period_start": "2026-08-21", "period_end": "2026-09-20"}', '1757637.00', '이전달 사용량 오류 : 실제-16937 청구-16537 월말-17162', '/uploads/invoice_3ac727c96aa845b79469e7ca25d679e2.jpg', 'Si oe\r\n(am PARKVIEW  APARTOAERTS) Nomor : 093/X/2026\r\nPEMAKAIAN LISTRIK & AIR / CALCULATION CONSUMPTION\r\nBULAN TAGIH : OKTOBER 2026\r\nJATUH TEMPO: 15 OKTOBER 2026\r\nMaria Goretti Panjaitan\r\nAPARTEMEN SLIPI Unit : 1/18-C Daya: 10,6 KVA\r\nJL. LETJEND S. PARMAN KAV. 22-24 Awal Catat :21 Agustus 2026\r\nJAKARTA BARAT - 11480 Akhir Catat :20 September 2026\r\nKeterangan / Description Jumlah / Total\r\nLISTRIK / ELECTRICITY\r\nAwal / Previous — Akhir / Current KWH Consumption\r\n16.537 - 17.183 = 646\r\nPemakaian / Usage Charge = 646 KWHxRp. 1.699,53 1.097.896\r\nUtilitas = Rp. 583.000 583.000\r\nPBJT-TL = 2,40% * 1.680.896 a0342\r\nBiaya Administrasi 6000\r\nPemakaian Listrik / Electricty Consumption : 1.727.237\r\nAIR / WATER\r\nAwal / Previous — Akhir / Current M3 Consumption Rate (M3)\r\n7.234 « 7.234 ie)\r\nPemakaian / Usage Charge =0x Rp. 21.500\r\nAbudemen / Subscription Fee = Rp. 30.400 30.400\r\nPemakaian Air / Water Consumption : 30.400\r\n1.757.637\r\nPembayaran harap ditransfer ke\r\nBANK BRI ACC : 0417 — 01 000 452 303 A/N: PPPSRS APARTEMEN SLIPI\r\n- Pembayaran dapat dilakukan melalui kasir dengan menggunakan kartu Debet/Kredit berlogo Visa & Master\r\n- Untuk pembayaran transfer harap konfirmasi melalui Whatsapp 0817-7078-4666 Tlp : (021)5332777/6\r\natau Email : slipi.finance@gmail.com\r\nKeterlambatan pembayaran iuran kewajiban dikenakan denda, untuk bulan pertama 3 %,\r\nbulan kedua 6 % dan bulan ketiga 9 %,sesuai dengan tata tertib kepenghunian AKTA NO:\r\n5 Tanggal 14 Desember 2019\r\nEN.\r\nAes SON\r\nA | APARTEMENTS\\', '2026-10-27 13:39:05', '2026-10-27 13:53:09', 1),
(2, '2026-09', '093/IX/2026', 'APARTEMEN SLIPI', '1/18-C', '2026-09-15', '2026-09-02', 1, '[{"name": "전기 사용요금", "amount": "305915.00"}, {"name": "공용설비비 (Utilitas)", "amount": "583000.00"}, {"name": "전기세금 (PBJT-TL)", "amount": "21334.00"}, {"name": "행정비", "amount": "6000.00"}, {"name": "수도 사용요금", "amount": "301000.00"}, {"name": "수도 기본료", "amount": "34000.00"}]', '{"electricity": {"previous": "16357.00", "current": "16537.00", "usage": "180.00", "rate": "1699.53"}, "water": {"previous": "7220.00", "current": "7234.00", "usage": "14.00", "rate": "21500.00"}, "period_start": "2026-07-21", "period_end": "2026-08-20"}', '1251249.00', '', '/uploads/invoice_f736ff01a75a4ebeb373bcab0c2561b9.jpg', 'Wlipi=\r\n——— Nomor : 093/1X/2026\r\nPEMAKAIAN LISTRIK & AIR / CALCULATION CONSUMPTION\r\nBULAN TAGIH : SEPTEMBER 2026\r\nJATUH TEMPO: 15 SEPTEMBER 2026\r\nMaria Goretti Panjaitan\r\nAPARTEMEN SLIPI Unit : 1/18-C Daya: 10,6 KVA\r\nJL. LETJEND S. PARMAN KAV. 22-24 Awal Catat :21 Juli 2026\r\nJAKARTA BARAT - 11480 Akhir Catat :20 Agustus 2026\r\nKeterangan / Description Jumlah / Total\r\nLISTRIK / ELECTRICITY\r\nAwal / Previous — Akhir / Current KWH Consumption\r\n16.357 - 16.537 = 180\r\nPemakaian / Usage Charge = 180 KWHxRp. 1.699,53 305.915\r\nUtilitas = Rp. 583.000 583.000\r\nPBIT-TL = 2,40% * 888.915 21.334\r\nBiaya Administrasi 6000\r\nPemakaian Listrik / Electricty Consumption : 916.249\r\nAIR / WATER\r\nAwal / Previous — Akhir / Current M3 Consumption Rate (M3)\r\n7.220 - 7.234 14\r\nPemakaian / Usage Charge =14xRp. 21.500 301.000\r\nAbudemen / Subscription Fee = Rp. 30.400 331.400\r\nPemakaian Air / Water Consumption : 331.400\r\n1.207.649\r\nPembayaran harap ditransfer ke :\r\nBANK BRI ACC : 0417 — 01 000 452 303 A/N: PPPSRS APARTEMEN SLIPI\r\n- Pembayaran dapat dilakukan melalui kasir dengan menggunakan kartu Debet/Kredit berlogo Visa & Master\r\n- Untuk pembayaran transfer harap konfirmasi melalui Whatsapp 0817-7078-4666 Tlp : (021)5332777/6\r\natau Email : slipi.finance@gmail.com\r\nKeterlambatan pembayaran iuran kewajiban dikenakan denda, untuk bulan pertama 3 %,\r\nbulan kedua 6 % dan bulan ketiga 9 %,sesuai dengan tata tertib kepenghunian AKTA NO:\r\n5 Tanggal 14 Desember 2019', '2026-10-27 13:52:11', '2026-10-27 13:52:11', 1),
(3, '2026-08', '093/VIII/2026', 'APARTEMEN SLIPI', '1/18-C', '2026-08-15', '2026-08-13', 1, '[{"name": "전기 사용요금", "amount": "1065605.00"}, {"name": "공용설비비 (Utilitas)", "amount": "583000.00"}, {"name": "전기세금 (PBJT-TL)", "amount": "39567.00"}, {"name": "행정비", "amount": "6000.00"}, {"name": "수도 사용요금", "amount": "279500.00"}, {"name": "수도 기본료", "amount": "30400.00"}]', '{"electricity": {"previous": "15730.00", "current": "16357.00", "usage": "627.00", "rate": "1699.53"}, "water": {"previous": "7207.00", "current": "7220.00", "usage": "13.00", "rate": "21500.00"}, "period_start": "2026-06-21", "period_end": "2026-07-20"}', '2004071.00', '', '/uploads/invoice_4971c054349f4094b2d1bc5f76de0769.jpg', 'Sli ce\r\nae Nomor : 093/VIII/2026\r\nPEMAKAIAN LISTRIK & AIR / CALCULATION CONSUMPTION\r\nBULAN TAGIH : AGUSTUS 2026\r\nJATUH TEMPO: 15 AGUSTUS 2026\r\n\r\nMaria Goretti Panjaitan\r\n\r\nAPARTEMEN SLIPI Unit : 1/18-C Daya: 10,6 KVA\r\n\r\nJL. LETJEND S. PARMAN KAV. 22-24 Awal Catat :21 Juni 2026\r\n\r\nJAKARTA BARAT - 11480 Akhir Catat :20 Juli 2026\r\n\r\nKeterangan / Description Jumlah / Total\r\n\r\nLISTRIK / ELECTRICITY\r\n\r\nAwal / Previous — Akhir / Current KWH Consumption\r\n\r\n15.730 - 16.357 = 627\r\n\r\nPemakaian / Usage Charge = 627 KWHxRp. 1.699,53 1.065.605\r\nUtilitas = Rp. 583.000 583.000\r\nPBIT-TL = 2,40% * 1.648.605 a087\r\nBiaya Administrasi 6000\r\nPemakaian Listrik / Electricty Consumption : 1.694.171\r\nAIR / WATER\r\n\r\nAwal / Previous — Akhir / Current M3 Consumption Rate (M3)\r\n\r\n7.207 : 7.220 13\r\n\r\nPemakaian / Usage Charge =13xRp. 21.500 279.500\r\nAbudemen / Subscription Fee = Rp. 30.400 309.900\r\nPemakaian Air / Water Consumption : 309.900\r\n2.008.071\r\nPembayaran harap ditransfer ke :\r\n\r\nBANK BRI ACC : 0417 — 01 000 452 303 A/N: PPPSRS APARTEMEN SLIPI\r\n\r\n- Pembayaran dapat dilakukan melalui kasir dengan menggunakan kartu Debet/Kredit berlogo Visa & Master\r\n\r\n- Untuk pembayaran transfer harap konfirmasi melalui Whatsapp 0817-7078-4666 Tlp : (021)5332777/6\r\n\r\natau Email : slipi.finance@gmail.com\r\n\r\nKeterlambatan pembayaran iuran kewajiban dikenakan denda, untuk bulan pertama 3 %,\r\nbulan kedua 6 % dan bulan ketiga 9 %,sesuai dengan tata tertib kepenghunian AKTA NO:\r\n\r\n5 Tanggal 14 Desember 2019', '2026-10-27 19:40:31', '2026-10-27 19:40:31', 1),
(4, '2026-01', '093/1/2026', 'APARTEMEN SLIPI', '1/18-C', '2026-01-15', '2026-01-05', 1, '[{"name": "전기 사용요금", "amount": "929643.00"}, {"name": "공용설비비 (Utilitas)", "amount": "583000.00"}, {"name": "전기세금 (PBJT-TL)", "amount": "36303.00"}, {"name": "행정비", "amount": "6000.00"}, {"name": "수도 사용요금", "amount": "322500.00"}, {"name": "수도 기본료", "amount": "30400.00"}]', '{"electricity": {"previous": "12005.00", "current": "12552.00", "usage": "547.00", "rate": "1699.53"}, "water": {"previous": "7133.00", "current": "7148.00", "usage": "15.00", "rate": "21500.00"}, "period_start": "2025-11-21", "period_end": "2025-12-20"}', '1907846.00', '', '/uploads/invoice_697b725d114a4f3cab11bfdba4c2f22f.jpg', 'SG aa\r\n(am PARKVIEW APARTOAENTS) Nomor :093/1/2026\r\nPEMAKAIAN LISTRIK & AIR / CALCULATION CONSUMPTION\r\nBULAN TAGIH : JANUAR! 2026\r\nJATUH TEMPO : 15 JANUARI 2026\r\nMaria Goretti Panjaitan\r\nAPARTEMEN SLIPI Unit : 1/18-C Daya: 10,6 KVA\r\nJL. LETJEND S. PARMAN KAV. 22-24 Awal Catat :21 November 2025\r\nJAKARTA BARAT - 11480 Akhir Catat :20 Desember 2025\r\nKeterangan / Description Jumlah / Total\r\nLISTRIK / ELECTRICITY\r\nAwal / Previous — Akhir / Current KWH Consumption\r\n12.005 -12.552 = 547\r\nPemakaian / Usage Charge = 547 KWHxRp. 1.699,53 929.643\r\nUtilitas = Rp. 583.000 583.000\r\nPBIT-TL = 2,40% * 1.512.643 36.303\r\nBiaya Administrasi 6000\r\nPemakaian Listrik / Electricty Consumption : 1.554.946\r\nAIR / WATER\r\nAwal / Previous — Akhir / Current M3 Consumption Rate (M3)\r\n7.133 - 7.148 15\r\nPemakaian / Usage Charge =15xRp. 21.500 322.500\r\nAbudemen / Subscription Fee = Rp. 30.400 352.900\r\nPemakaian Air / Water Consumption : 352.900\r\n1.907.846\r\nPembayaran harap ditransfer ke :\r\nBANK BRI ACC : 0417 — 01 000 452 303 A/N: PPPSRS APARTEMEN SLIPI\r\n- Pembayaran dapat dilakukan melalui kasir dengan menggunakan kartu Debet/Kredit berlogo Visa & Master\r\n- Untuk pembayaran transfer harap konfirmasi melalui Whatsapp 0817-7078-4666 Tlp : (021)5332777/6\r\natau Email : slipi.finance@gmail.com\r\nKeterlambatan pembayaran iuran kewajiban dikenakan denda, untuk bulan pertama 3 %,\r\nbulan kedua 6 % dan bulan ketiga 9 %,sesuai dengan tata tertib kepenghunian AKTA NO:\r\n5 Tanggal 14 Desember 2019', '2026-10-27 19:47:10', '2026-10-27 19:47:10', 1),
(5, '2026-02', '093/II/2026', 'APARTEMEN SLIP!', '1/18-C', '2026-02-15', '2026-02-02', 1, '[{"name": "전기 사용요금", "amount": "625427.04"}, {"name": "공용설비비 (Utilitas)", "amount": "583000.00"}, {"name": "전기세금 (PBJT-TL)", "amount": "29002.00"}, {"name": "행정비", "amount": "6000.00"}, {"name": "수도 사용요금", "amount": "150500.00"}, {"name": "수도 기본료", "amount": "30400.00"}]', '{"electricity": {"previous": "12552.00", "current": "12920.00", "usage": "368.00", "rate": "1699.53"}, "water": {"previous": "7148.00", "current": "7155.00", "usage": "7.00", "rate": "21500.00"}, "period_start": "2025-12-21", "period_end": "2026-01-20"}', '1424329.00', '', '/uploads/invoice_f1fa48759cb5453fb36f41c8f30a20d7.jpg', 'aes or\r\n{am PARKVIEW APARTMENTS) Nomor : 093 /11/2026\r\nPEMAKAIAN LISTRIK & AIR / CALCULATION CONSUMPTION\r\nBULAN TAGIH : FEBRUARI 2026\r\nJATUH TEMPO : 15 FEBRUARI 2026\r\n\r\nMaria Goretti Panjaitan\r\nAPARTEMEN SLIP! Unit : 1/18-C Daya: 10,6 KVA\r\nJL. LETJEND S. PARMAN KAV. 22-24 Awal Catat :21 Desember 2025\r\nJAKARTA BARAT - 11480 Akhir Catat :20 Januari 2026\r\n\r\nKeterangan / Description Jumlah / Total\r\nLISTRIK / ELECTRICITY\r\nAwal / Previous - Akhir / Current KWH Consumption\r\n12.552 -12.920 = 368\r\nPemakaian / Usage Charge = 368 KWHxRp. 1.699,53 6251427:\r\nUtilitas = Rp. 583.000 583.000\r\nPBIT-TL = 2,40% * 1.208.427 29.002\r\nBiaya Administrasi 6000\r\nPemakaian Listrik / Electricty Consumption : 1.243.429\r\nAIR / WATER\r\nAwal / Previous — Akhir / Current M3 Consumption — Rate (M3)\r\n\r\n7.148 * T5S: a\r\n\r\nPemakaian / Usage Charge = 7 x Rp. 21.500 150.500\r\nAbudemen / Subscription Fee = Rp. 30.400 180.900\r\nPemakaian Air / Water Consumption : 180.900\r\nTOTAL PEMAKAIAN LISTRIK & AIR / TOTAL UTILITIES CONSUMPTION | s«i.424.3289 |\r\nPembayaran harap ditransfer ke\r\nBANK BRI ACC : 0417 — 01 000 452 303 A/N: PPPSRS APARTEMEN SLIPI\r\n- Pembayaran dapat dilakukan melalui kasir dengan menggunakan kartu Debet/Kredit berlogo Visa & Master\r\n- Untuk pembayaran transfer harap konfirmasi melalui Whatsapp 0817-7078-4666 Tlp : (021)5332777/6\r\natau Email : slipi.finance@gmail.com\r\nKeterlambatan pembayaran iuran kewajiban dikenakan denda, untuk bulan pertama 3 %,\r\nbulan kedua 6 % dan bulan ketiga 9 %,sesuai dengan tata tertib kepenghunian AKTA NO :\r\n5 Tanggal 14 Desember 2019', '2026-10-27 19:49:08', '2026-10-27 19:49:08', 1),
(6, '2026-03', '093/111/2026', 'APARTEMEN SLIPI', '1/18-C', '2026-03-15', '2026-03-02', 1, '[{"name": "전기 사용요금", "amount": "562544.00"}, {"name": "공용설비비 (Utilitas)", "amount": "583000.00"}, {"name": "전기세금 (PBJT-TL)", "amount": "27493.00"}, {"name": "행정비", "amount": "6000.00"}, {"name": "수도 사용요금", "amount": "172000.00"}, {"name": "수도 기본료", "amount": "30400.00"}]', '{"electricity": {"previous": "12920.00", "current": "13251.00", "usage": "331.00", "rate": "1699.53"}, "water": {"previous": "7155.00", "current": "7163.00", "usage": "8.00", "rate": "21500.00"}, "period_start": "2026-01-21", "period_end": "2026-02-20"}', '1381437.00', '', '/uploads/invoice_3e8f4f5673324559a5b095037f92650c.jpg', 'SG or\r\nSat AEN arereeeTst Nomor : 093/111/2026\r\nPEMAKAIAN LISTRIK & AIR / CALCULATION CONSUMPTION\r\nBULAN TAGIH : MARET 2026\r\nJATUH TEMPO : 15 MARET 2026\r\nMaria Goretti Panjaitan\r\nAPARTEMEN SLIPI Unit : 1/18-C Daya: 10,6 KVA\r\nJL. LETJEND S. PARMAN KAV. 22-24 Awal Catat :21 Januari 2026\r\nJAKARTA BARAT - 11480 Akhir Catat : 20 Februari 2026\r\nKeterangan / Description Jumlah / Total\r\nLISTRIK / ELECTRICITY\r\nAwal / Previous — Akhir / Current KWH Consumption\r\n12.920 - 13.251 = 331\r\nPemakaian / Usage Charge = 331 KWHxRp. 1.699,53 562.544\r\nUtilitas = Rp. 583.000 583.000\r\nPBIT-TL = 2,40% * 1.145.544 27.493\r\nBiaya Administrasi 6000\r\nPemakaian Listrik / Electricty Consumption : 1.179.037\r\nAIR / WATER\r\nAwal / Previous — Akhir / Current M3 Consumption Rate (M3)\r\n7.155, - 7.163 8\r\nPemakaian / Usage Charge =8 x Rp. 21.500 172.000\r\nAbudemen / Subscription Fee = Rp. 30.400 202.400\r\nPemakaian Air / Water Consumption : 202.400\r\n1.381.437\r\nPembayaran harap ditransfer ke :\r\nBANK BRI ACC : 0417 - 01 000 452 303 A/N: PPPSRS APARTEMEN SLIPI\r\n- Pembayaran dapat dilakukan melalui kasir dengan menggunakan kartu Debet/Kredit berlogo Visa & Master\r\n- Untuk pembayaran transfer harap konfirmasi melalui Whatsapp 0817-7078-4666 Tlp : (021)5332777/6\r\natau Email : slipi.finance@gmail.com\r\nKeterlambatan pembayaran iuran kewajiban dikenakan denda, untuk bulan pertama 3 %,\r\nbulan kedua 6 % dan bulan ketiga 9 %,sesuai dengan tata tertib kepenghunian AKTA NO:\r\n5 Tanggal 14 Desember 2019', '2026-10-27 19:50:23', '2026-10-27 19:50:23', 1),
(7, '2026-04', '093/IV/2026', 'APARTEMEN SLIPI', '1/18-C', '2026-04-15', '2026-04-06', 1, '[{"name": "전기 사용요금", "amount": "630526.00"}, {"name": "공용설비비 (Utilitas)", "amount": "583000.00"}, {"name": "전기세금 (PBJT-TL)", "amount": "29124.62"}, {"name": "행정비", "amount": "6000.00"}, {"name": "수도 사용요금", "amount": "301000.00"}, {"name": "수도 기본료", "amount": "30400.00"}]', '{"electricity": {"previous": "13251.00", "current": "13622.00", "usage": "371.00", "rate": "1699.53"}, "water": {"previous": "7163.00", "current": "7177.00", "usage": "14.00", "rate": "21500.00"}, "period_start": "2026-02-21", "period_end": "2026-03-20"}', '1580050.00', '', '/uploads/invoice_ab9a11e5983145f186be27de129b5f9a.jpg', 'Slivt=\r\nSa reeves Arne Nomor : 093/IV/2026\r\nPEMAKAIAN LISTRIK & AIR / CALCULATION CONSUMPTION\r\nBULAN TAGIH : APRIL 2026\r\nJATUH TEMPO: 15 APRIL 2026\r\n\r\nMaria Goretti Panjaitan\r\n\r\nAPARTEMEN SLIPI Unit : 1/18-C Daya: 10,6 KVA\r\n\r\nJL. LETJEND S. PARMAN KAV. 22-24 Awal Catat :21 Februari 2026\r\nJAKARTA BARAT - 11480 Akhir Catat :20 Maret 2026\r\n\r\nKeterangan / Description Jumlah / Total\r\n\r\nLISTRIK / ELECTRICITY\r\n\r\nAwal / Previous — Akhir / Current KWH Consumption\r\n\r\n13.251 -13.622 =371\r\n\r\nPemakaian / Usage Charge = 371 KWHxRp. 1.699,53 630.526\r\nUtilitas = Rp.583.000 583.000\r\nPBIT-TL = 2,40% * 1.213.526 a2:225.\r\nBiaya Administrasi 6000\r\nPemakaian Listrik / Electricty Consumption : 1.248.650\r\nAIR / WATER\r\n\r\nAwal / Previous — Akhir / Current M3 Consumption Rate (M3)\r\n\r\n7.163 = 7.177 14\r\n\r\nPemakaian / Usage Charge =14xRp. 21.500 301.000\r\nAbudemen / Subscription Fee = Rp. 30.400 331.400\r\nPemakaian Air / Water Consumption : 331.400\r\n1.580.050\r\nPembayaran harap ditransfer ke\r\n\r\nBANK BRI ACC : 0417 — 01 000 452 303 A/N: PPPSRS APARTEMEN SLIPI\r\n\r\n- Pembayaran dapat dilakukan melalui kasir dengan menggunakan kartu Debet/Kredit berlogo Visa & Master\r\n\r\n- Untuk pembayaran transfer harap konfirmasi melalui Whatsapp 0817-7078-4666 Tlp : (021)5332777/6\r\n\r\natau Email : slipi.finance@gmail.com\r\n\r\nKeterlambatan pembayaran iuran kewajiban dikenakan denda, untuk bulan pertama 3 %,\r\nbulan kedua 6 % dan bulan ketiga 9 %,sesuai dengan tata tertib kepenghunian AKTA NO:\r\n\r\n5 Tanggal 14 Desember 2019', '2026-10-27 20:06:24', '2026-10-27 20:06:24', 1),
(8, '2026-05', '093/V/2026', 'APARTEMEN SLIPI', '1/18-C', '2026-05-15', '2026-05-04', 1, '[{"name": "전기 사용요금", "amount": "1011220.00"}, {"name": "공용설비비 (Utilitas)", "amount": "583000.00"}, {"name": "전기세금 (PBJT-TL)", "amount": "38261.28"}, {"name": "행정비", "amount": "6000.00"}, {"name": "수도 사용요금", "amount": "150500.00"}, {"name": "수도 기본료", "amount": "30400.00"}]', '{"electricity": {"previous": "13622.00", "current": "14217.00", "usage": "595.00", "rate": "1699.53"}, "water": {"previous": "7177.00", "current": "7184.00", "usage": "7.00", "rate": "21500.00"}, "period_start": "2026-03-21", "period_end": "2026-04-20"}', '1819381.00', '', '/uploads/invoice_0cca7f7d285a4ad29787c5392090867e.jpg', 'lint =\r\nLO Une erty Nomor : 093/V/2026\r\nPEMAKAIAN LISTRIK & AIR / CALCULATION CONSUMPTION\r\nBULAN TAGIH : MEI 2026\r\nJATUH TEMPO: 15 MEI 2026\r\n\r\nMaria Goretti Panjaitan\r\n\r\nAPARTEMEN SLIPI Unit : 1/18-C Daya: 10,6 KVA\r\n\r\nJL. LETJEND S. PARMAN KAV. 22-24 Awal Catat :21 Maret 2026\r\n\r\nJAKARTA BARAT - 11480 Akhir Catat :20 April 2026\r\n\r\nKeterangan / Description Jumlah / Total\r\n\r\nLISTRIK / ELECTRICITY\r\n\r\nAwal / Previous — Akhir / Current KWH Consumption\r\n\r\n13.622 -14.217 =595\r\n\r\nPemakaian / Usage Charge = 595 KWHxRp. 1.699,53 1.011.220\r\nUtilitas = Rp. 583.000 583.000\r\nPBIT-TL = 2,40% * 1.594.220 38.261\r\nBiaya Administrasi 6000\r\nPemakaian Listrik / Electricty Consumption : 1.638.481\r\nAIR / WATER\r\n\r\nAwal / Previous — Akhir / Current M3 Consumption Rate (M3)\r\n\r\n7.177 - 7.184 7\r\n\r\nPemakaian / Usage Charge =7 x Rp. 21.500 150.500\r\nAbudemen / Subscription Fee = Rp. 30.400 180.900\r\nPemakaian Air / Water Consumption : 180.900\r\n1.819.381\r\nPembayaran harap ditransfer ke :\r\n\r\nBANK BRI ACC : 0417 — 01 000 452 303 A/N: PPPSRS APARTEMEN SLIPI\r\n\r\n- Pembayaran dapat dilakukan melalui kasir dengan menggunakan kartu Debet/Kredit berlogo Visa & Master\r\n\r\n- Untuk pembayaran transfer harap konfirmasi melalui Whatsapp 0817-7078-4666 Tlp : (021)5332777/6\r\n\r\natau Email : slipi.finance@gmail.com\r\n\r\nKeterlambatan pembayaran iuran kewajiban dikenakan denda, untuk bulan pertama 3 %,\r\nbulan kedua 6 % dan bulan ketiga 9 %,sesuai dengan tata tertib kepenghunian AKTA NO :\r\n\r\n5 Tanggal 14 Desember 2019', '2026-10-27 20:25:47', '2026-10-27 20:25:47', 1),
(9, '2026-06', '093/V1/2026', 'APARTEMEN SLIPI', '1/18-C', '2026-06-15', '2026-06-08', 1, '[{"name": "전기 사용요금", "amount": "1352826.00"}, {"name": "공용설비비 (Utilitas)", "amount": "583000.00"}, {"name": "전기세금 (PBJT-TL)", "amount": "46460.00"}, {"name": "행정비", "amount": "6000.00"}, {"name": "수도 사용요금", "amount": "193500.00"}, {"name": "수도 기본료", "amount": "30400.00"}]', '{"electricity": {"previous": "14217.00", "current": "15013.00", "usage": "796.00", "rate": "1700.00"}, "water": {"previous": "7184.00", "current": "7193.00", "usage": "9.00", "rate": "21500.00"}, "period_start": "2026-04-21", "period_end": "2026-05-20"}', '2212185.00', '', '/uploads/invoice_027737181c2941d7bf8e6aa900d001ab.jpg', 'Slivi=\r\n{3/m PARKVIEW  APARTIAENTS) Nomor :093/V1/2026\r\nPEMAKAIAN LISTRIK & AIR / CALCULATION CONSUMPTION\r\nBULAN TAGIH : JUNI 2026\r\nJATUH TEMPO: 15 JUNI 2026\r\nMaria Goretti Panjaitan\r\nAPARTEMEN SLIPI Unit : 1/18-C Daya: 10,6 KVA\r\nJL. LETJEND S. PARMAN KAV. 22-24 Awal Catat :21 April 2026\r\nJAKARTA BARAT - 11480 Akhir Catat :20 Mei 2026\r\nKeterangan / Description Jumlah / Total\r\nLISTRIK / ELECTRICITY\r\nAwal / Previous — Akhir / Current KWH Consumption\r\n14.217-15.013 = 796\r\nPemakaian / Usage Charge = 796 KWHxRp. 1.699,53 1.352.826\r\nUtilitas = Rp. 583.000 583.000\r\nPBIT-TL = 2,40% * 1.935.826 SoAS\r\nBiaya Administrasi 6000\r\nPemakaian Listrik / Electricty Consumption : 1.988.285\r\nAIR / WATER\r\nAwal / Previous — Akhir / Current M3 Consumption Rate (M3)\r\n7.184 : 7.193 9\r\nPemakaian / Usage Charge =9 x Rp. 21.500 193.500\r\nAbudemen / Subscription Fee = Rp. 30.400 223.900\r\nPemakaian Air / Water Consumption : 223.900\r\n[TOTALPEMAKAIAN LISTRIK &AIR/ TOTAL UTILITIES CONSUMPTION | 2.212.185 |\r\nPembayaran harap ditransfer ke\r\nBANK BRI ACC : 0417 — 01 000 452 303 A/N: PPPSRS APARTEMEN SLIPI\r\n- Pembayaran dapat dilakukan melalui kasir dengan menggunakan kartu Debet/Kredit berlogo Visa & Master\r\n- Untuk pembayaran transfer harap konfirmasi melalui Whatsapp 0817-7078-4666 Tlp : (021)5332777/6\r\natau Email : slipi.finance@gmail.com\r\nKeterlambatan pembayaran iuran kewajiban dikenakan denda, untuk bulan pertama 3 %,\r\nbulan kedua 6 % dan bulan ketiga 9 %,sesuai dengan tata tertib kepenghunian AKTA NO:\r\n5 Tanggal 14 Desember 2019', '2026-10-27 20:34:51', '2026-10-27 20:34:51', 1),
(10, '2026-07', '093/VII/2026', 'APARTEMEN SLIP!', '1/18-C', '2026-07-15', '2026-07-06', 1, '[{"name": "전기 사용요금", "amount": "1218563.00"}, {"name": "공용설비비 (Utilitas)", "amount": "583000.00"}, {"name": "전기세금 (PBJT-TL)", "amount": "43238.00"}, {"name": "행정비", "amount": "6000.00"}, {"name": "수도 사용요금", "amount": "301000.00"}, {"name": "수도 기본료", "amount": "30400.00"}]', '{"electricity": {"previous": "15013.00", "current": "15730.00", "usage": "717.00", "rate": "1700.00"}, "water": {"previous": "7193.00", "current": "7207.00", "usage": "14.00", "rate": "21500.00"}, "period_start": "2026-05-21", "period_end": "2026-06-20"}', '2182200.00', '', '/uploads/invoice_60c9804fe0364c44b0792bc5ea17fb34.jpg', 'Sli (bea\r\n————l Nomor : 093/VII/2026\r\nPEMAKAIAN LISTRIK & AIR / CALCULATION CONSUMPTION\r\nBULAN TAGIH : JULI2026\r\nJATUH TEMPO: 15 JULI 2026\r\nMaria Goretti Panjaitan\r\nAPARTEMEN SLIP! Unit : 1/18-C Daya: 10,6 KVA\r\nJL. LETJEND S. PARMAN KAV. 22-24 Awal Catat :21 Mei 2026\r\nJAKARTA BARAT - 11480 Akhir Catat :20 Juni 2026\r\nKeterangan / Description Jumlah / Total\r\nLISTRIK / ELECTRICITY\r\nAwal / Previous — Akhir / Current KWH Consumption\r\n15.013 - 15.730 =717\r\nPemakaian / Usage Charge = 717 KWHxRp. 1.699,53 1.218.563\r\nUtilitas = Rp.583.000 583.000\r\nPBIT-TL = 2,40% * 1.801.563 43238\r\nBiaya Administrasi 6000\r\nPemakaian Listrik / Electricty Consumption : 1.850.800\r\nAIR / WATER\r\nAwal / Previous — Akhir / Current M3 Consumption Rate (M3)\r\n7.193 . 7.207 14\r\nPemakaian / Usage Charge =14xRp. 21.500 301.000\r\nAbudemen / Subscription Fee = Rp. 30.400 331.400\r\nPemakaian Air / Water Consumption : 331.400\r\n2.182.200\r\nPembayaran harap ditransfer ke\r\nBANK BRI ACC : 0417 — 01 000 452 303 A/N: PPPSRS APARTEMEN SLIPI\r\n- Pembayaran dapat dilakukan melalui kasir dengan menggunakan kartu Debet/Kredit berlogo Visa & Master\r\n- Untuk pembayaran transfer harap konfirmasi melalui Whatsapp 0817-7078-4666 Tlp : (021)5332777/6\r\natau Email : slipi.finance@gmail.com\r\nKeterlambatan pembayaran iuran kewajiban dikenakan denda, untuk bulan pertama 3 %,\r\nbulan kedua 6 % dan bulan ketiga 9 %,sesuai dengan tata tertib kepenghunian AKTA NO:\r\n5 Tanggal 14 Desember 2019', '2026-10-27 20:37:35', '2026-10-27 20:39:19', 1);
UNLOCK TABLES;

-- --------------------------------------------------------
-- Table structure for `golf_contacts`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `golf_contacts`;
CREATE TABLE `golf_contacts` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `nickname` varchar(100) NOT NULL,
  `phone` varchar(80) NOT NULL,
  `address` varchar(500) NOT NULL,
  `memo` text NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  `owner_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_golf_contacts_owner` (`owner_id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dumping data for table `golf_contacts` (6 rows)
LOCK TABLES `golf_contacts` WRITE;
INSERT INTO `golf_contacts` (`id`, `name`, `nickname`, `phone`, `address`, `memo`, `created_at`, `updated_at`, `owner_id`) VALUES
(1, '최미영', 'choi', '', 'APT Taman Raja', '', '2026-10-27 16:00:00', '2026-10-27 16:00:00', 1),
(2, '박수경', 'park', '', 'APT Taman Raja', '', '2026-10-27 16:00:17', '2026-10-27 16:00:17', 1),
(3, '이정임', 'Lee', '', 'APT Taman Raja', '', '2026-10-27 16:00:36', '2026-10-27 16:00:36', 1),
(4, '최은영', 'Sera', '', 'APT Aspen', '', '2026-10-27 16:00:50', '2026-10-27 16:00:50', 1),
(5, '임희옥', 'Agnes', '', 'Premier', '', '2026-10-27 16:01:08', '2026-10-27 16:01:08', 1),
(6, '김숙진', 'Lucia', '', 'Premier', '', '2026-10-27 16:01:20', '2026-10-27 16:01:20', 1);
UNLOCK TABLES;

-- --------------------------------------------------------
-- Table structure for `golf_rounds`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `golf_rounds`;
CREATE TABLE `golf_rounds` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `played_on` date NOT NULL,
  `course_name` varchar(150) NOT NULL,
  `player_name` varchar(100) NOT NULL DEFAULT '본인',
  `front_score` smallint(6) NOT NULL,
  `back_score` smallint(6) NOT NULL,
  `companions_json` text NOT NULL,
  `memo` text NOT NULL,
  `photo_path` varchar(255) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  `golf_club` varchar(150) NOT NULL DEFAULT '',
  `player_nickname` varchar(100) NOT NULL DEFAULT '',
  `hole_scores_json` text DEFAULT NULL,
  `owner_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_golf_played_on` (`played_on`,`id`),
  KEY `idx_golf_rounds_owner` (`owner_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dumping data for table `golf_rounds` (2 rows)
LOCK TABLES `golf_rounds` WRITE;
INSERT INTO `golf_rounds` (`id`, `played_on`, `course_name`, `player_name`, `front_score`, `back_score`, `companions_json`, `memo`, `photo_path`, `created_at`, `updated_at`, `golf_club`, `player_nickname`, `hole_scores_json`, `owner_id`) VALUES
(1, '2026-07-17', 'Old Course', '정주형', 53, 51, '[{"name": "최미영", "nickname": "choi", "total_score": 102}, {"name": "박수경", "nickname": "park", "total_score": 102}]', '20260717 TR 3인 첫 라운드', '/uploads/golf_1c40efbe3fdf44349509669deb21ba87.jpg', '2026-10-27 13:30:06', '2026-10-27 13:30:06', 'Jagorawi', '', NULL, 1),
(2, '2026-07-24', 'New Course', '정주형', 53, 54, '[{"name": "최미영", "nickname": "choi", "total_score": 98}, {"name": "박수경", "nickname": "park", "total_score": 106}]', 'TR 2번째 라운드', '/uploads/golf_4ed97ce25c1f4dc18c4bcbe6efbfc4d6.jpg', '2026-10-27 13:32:09', '2026-10-27 13:32:09', 'Jagorawi', '', NULL, 1);
UNLOCK TABLES;

-- --------------------------------------------------------
-- Table structure for `personal_profile`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `personal_profile`;
CREATE TABLE `personal_profile` (
  `id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `nickname` varchar(100) NOT NULL,
  `updated_at` datetime NOT NULL,
  `owner_id` bigint(20) NOT NULL,
  PRIMARY KEY (`owner_id`,`id`),
  KEY `idx_personal_profile_owner` (`owner_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dumping data for table `personal_profile` (1 rows)
LOCK TABLES `personal_profile` WRITE;
INSERT INTO `personal_profile` (`id`, `name`, `nickname`, `updated_at`, `owner_id`) VALUES
(1, '정주형', 'Veronica', '2026-10-27 15:59:26', 1);
UNLOCK TABLES;

-- --------------------------------------------------------
-- Table structure for `pet_lineage`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `pet_lineage`;
CREATE TABLE `pet_lineage` (
  `pet_id` int(11) NOT NULL,
  `owner_id` bigint(20) NOT NULL,
  `generation_no` int(11) NOT NULL,
  PRIMARY KEY (`owner_id`,`pet_id`),
  KEY `idx_pet_lineage_generation` (`owner_id`,`generation_no`),
  KEY `fk_pet_lineage_pet` (`pet_id`),
  CONSTRAINT `fk_pet_lineage_pet` FOREIGN KEY (`pet_id`) REFERENCES `pets` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dumping data for table `pet_lineage` (17 rows)
LOCK TABLES `pet_lineage` WRITE;
INSERT INTO `pet_lineage` (`pet_id`, `owner_id`, `generation_no`) VALUES
(1, 1, 1),
(2, 1, 1),
(3, 1, 1),
(4, 1, 1),
(5, 1, 2),
(6, 1, 2),
(7, 1, 2),
(8, 1, 2),
(9, 1, 2),
(10, 1, 2),
(11, 1, 2),
(12, 1, 2),
(13, 1, 3),
(14, 1, 3),
(15, 1, 3),
(16, 1, 3),
(17, 1, 3);
UNLOCK TABLES;

-- --------------------------------------------------------
-- Table structure for `pet_records`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `pet_records`;
CREATE TABLE `pet_records` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `owner_id` bigint(20) NOT NULL,
  `pet_id` int(11) NOT NULL,
  `record_date` date NOT NULL,
  `content` text NOT NULL,
  `photo_path` varchar(255) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_pet_records_owner_pet_date` (`owner_id`,`pet_id`,`record_date`),
  KEY `fk_pet_records_pet` (`pet_id`),
  CONSTRAINT `fk_pet_records_pet` FOREIGN KEY (`pet_id`) REFERENCES `pets` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dumping data for table `pet_records` (9 rows)
LOCK TABLES `pet_records` WRITE;
INSERT INTO `pet_records` (`id`, `owner_id`, `pet_id`, `record_date`, `content`, `photo_path`, `created_at`) VALUES
(1, 1, 17, '2026-10-28', '똥글똥글 똥글이', '/uploads/20261028_220548_adaad682.jpg', '2026-10-28 22:05:48'),
(2, 1, 17, '2026-10-28', '나만 바라바', '/uploads/20261028_220613_226cee1d.jpg', '2026-10-28 22:06:13'),
(3, 1, 11, '2026-10-28', '센티한 목이', '/uploads/20261028_222217_4865f81a.jpg', '2026-10-28 22:22:17'),
(4, 1, 13, '2026-10-29', '부끄러운 울양', '/uploads/20261029_001046_7bf548e4.jpg', '2026-10-29 00:10:46'),
(5, 1, 13, '2026-10-29', '엄마가 좋은 울양', '/uploads/20261029_001134_0238468f.jpg', '2026-10-29 00:11:34'),
(6, 1, 13, '2026-10-29', '널부러진 울양', '/uploads/20261029_001218_cd3b3797.png', '2026-10-29 00:12:18'),
(7, 1, 1, '2026-10-29', '양이족보의 시작!🥰', '/uploads/20261029_001325_16de63d4.jpg', '2026-10-29 00:13:25'),
(8, 1, 1, '2026-10-29', '루시겠지?', '/uploads/20261029_001409_726c1b32.jpg', '2026-10-29 00:14:09'),
(9, 1, 11, '2026-10-29', '꼭 붙어있는 울목', '/uploads/20261029_152512_d8defd96.jpg', '2026-10-29 15:25:12');
UNLOCK TABLES;

-- --------------------------------------------------------
-- Table structure for `pets`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `pets`;
CREATE TABLE `pets` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `species` varchar(20) NOT NULL DEFAULT 'other',
  `registration_no` varchar(100) DEFAULT NULL,
  `sex` varchar(20) NOT NULL DEFAULT 'unknown',
  `birth_date` date DEFAULT NULL,
  `death_date` date DEFAULT NULL,
  `breed` varchar(100) NOT NULL DEFAULT '',
  `color` varchar(100) NOT NULL DEFAULT '',
  `microchip_no` varchar(100) NOT NULL DEFAULT '',
  `sire_id` int(11) DEFAULT NULL,
  `dam_id` int(11) DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'active',
  `notes` text NOT NULL,
  `photo_path` varchar(255) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  `owner_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_pets_registration_no` (`owner_id`,`registration_no`),
  KEY `idx_pets_name` (`name`),
  KEY `idx_pets_sire` (`sire_id`),
  KEY `idx_pets_dam` (`dam_id`),
  KEY `idx_pets_owner` (`owner_id`),
  CONSTRAINT `fk_pets_dam` FOREIGN KEY (`dam_id`) REFERENCES `pets` (`id`),
  CONSTRAINT `fk_pets_sire` FOREIGN KEY (`sire_id`) REFERENCES `pets` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dumping data for table `pets` (17 rows)
LOCK TABLES `pets` WRITE;
INSERT INTO `pets` (`id`, `name`, `species`, `registration_no`, `sex`, `birth_date`, `death_date`, `breed`, `color`, `microchip_no`, `sire_id`, `dam_id`, `status`, `notes`, `photo_path`, `created_at`, `updated_at`, `owner_id`) VALUES
(1, 'Lucy', 'cat', NULL, 'male', NULL, NULL, '', '', '', NULL, NULL, 'deceased', '', '/uploads/20261028_215056_857c4f56.jpg', '2026-10-28 19:48:10', '2026-10-28 21:50:56', 1),
(2, '니콜', 'cat', NULL, 'male', NULL, NULL, '', '', '', NULL, NULL, 'deceased', '', '/uploads/20261028_215206_efaef43e.jpg', '2026-10-28 20:03:49', '2026-10-28 21:52:06', 1),
(3, '니키', 'cat', NULL, 'female', NULL, NULL, '', '', '', NULL, NULL, 'deceased', '', '/uploads/20261028_215238_7f8a245b.jpg', '2026-10-28 20:04:19', '2026-10-28 21:52:38', 1),
(4, '아지', 'cat', NULL, 'male', NULL, NULL, '', '', '', NULL, NULL, 'deceased', '', '/uploads/20261028_215316_41db172d.jpg', '2026-10-28 20:04:31', '2026-10-28 21:53:16', 1),
(5, '호', 'cat', NULL, 'male', NULL, NULL, '', '', '', 1, 3, 'active', '', '/uploads/20261028_203638_a387634c.jpg', '2026-10-28 20:36:38', '2026-10-28 21:50:34', 1),
(6, '랑', 'cat', NULL, 'male', NULL, NULL, '', '', '', 1, 3, 'active', '', '/uploads/20261028_203752_df90a178.jpg', '2026-10-28 20:37:06', '2026-10-28 21:50:02', 1),
(7, '꽁지', 'cat', NULL, 'male', NULL, NULL, '', '', '', 1, 3, 'active', '', '/uploads/20261028_203825_bce9487b.jpg', '2026-10-28 20:38:25', '2026-10-28 21:49:35', 1),
(8, '월', 'cat', NULL, 'male', NULL, NULL, '', '', '', 2, 3, 'deceased', '', '/uploads/20261028_215410_1f8c1ec9.jpg', '2026-10-28 21:54:10', '2026-10-28 21:54:10', 1),
(9, '화', 'cat', NULL, 'female', NULL, NULL, '', '', '', 2, 3, 'active', '', '/uploads/20261028_215451_0482896d.jpg', '2026-10-28 21:54:51', '2026-10-28 21:54:51', 1),
(10, '수', 'cat', NULL, 'male', NULL, NULL, '', '', '', 2, 3, 'active', '', '/uploads/20261028_215613_36ba7fe5.jpg', '2026-10-28 21:55:12', '2026-10-28 21:56:13', 1),
(11, '목', 'cat', NULL, 'female', NULL, NULL, '', '', '', 2, 3, 'active', '', '/uploads/20261028_215542_18cf0de7.jpg', '2026-10-28 21:55:42', '2026-10-28 21:55:42', 1),
(12, '금', 'cat', NULL, 'male', NULL, NULL, '', '', '', 2, 3, 'deceased', '', '/uploads/20261028_215650_5508e41e.jpg', '2026-10-28 21:56:50', '2026-10-28 21:56:50', 1),
(13, '태양', 'cat', NULL, 'male', NULL, NULL, '', '', '', 8, 11, 'active', '', '/uploads/20261028_215854_b0c76301.jpg', '2026-10-28 21:58:54', '2026-10-28 21:58:54', 1),
(14, '써니', 'cat', NULL, 'female', NULL, NULL, '', '', '', 8, 11, 'active', '', '/uploads/20261028_220016_30861095.jpg', '2026-10-28 22:00:16', '2026-10-28 22:00:16', 1),
(15, '밍', 'cat', NULL, 'female', NULL, NULL, '', '', '', 8, 11, 'active', '', '/uploads/20261028_220122_d6ff7f43.jpg', '2026-10-28 22:01:22', '2026-10-28 22:01:22', 1),
(16, '꼬맹', 'cat', NULL, 'female', NULL, NULL, '', '', '', NULL, NULL, 'active', '', '/uploads/20261028_233809_e0c34d18.jpg', '2026-10-28 22:03:53', '2026-10-28 23:38:09', 1),
(17, '똥글', 'cat', NULL, 'male', NULL, NULL, '', '', '', NULL, NULL, 'deceased', '', '/uploads/20261028_220424_365524f4.jpg', '2026-10-28 22:04:24', '2026-10-28 22:04:24', 1);
UNLOCK TABLES;

-- --------------------------------------------------------
-- Table structure for `study_dictations`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `study_dictations`;
CREATE TABLE `study_dictations` (
  `video_id` int(11) NOT NULL,
  `content` longtext NOT NULL,
  `updated_at` datetime NOT NULL,
  `owner_id` bigint(20) NOT NULL,
  PRIMARY KEY (`video_id`),
  KEY `idx_study_dictations_owner` (`owner_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dumping data for table `study_dictations` (7 rows)
LOCK TABLES `study_dictations` WRITE;
INSERT INTO `study_dictations` (`video_id`, `content`, `updated_at`, `owner_id`) VALUES
(1, 'Halo lagi kita tujuh kali ini\nsemua apa aja ya macam macam \nyo langsung aja kita kevideonya\nJadi madu tj ini yg fresh \nDipanen sudah matang\nProses farmasi seperti\n\nMadu tj ini diproduksi dengan teknologi modern botol tutup di tumbang di jelok\nOk kapan kelama ya sekarang\nKira kira apa aja ya\nYang pertama yaitu \nSehingga madu tj murni \nSangat baik untuk muda\nYang kedua lemon\n100% madu yang \nMereka yang aktive  sakit perut yang ketiga\nAkan vitamin ', '2026-10-27 14:33:06', 1),
(2, 'Video promosi kesehatan seimbangan\nHi semua\nMasih ingat dengan sempurna\nSudah ', '2026-10-26 23:21:04', 1),
(3, 'Bunda kenapa rico\nAku lapar bunda\nSabar riko\nBunda ada apa ya\nAyah lapar\nBunda masak\nLapar juga\nSekarang ayah\nMaaf ayah.bunda memasak apa\nBunda memasak sayur\nSuka ayam goreng\nSelain makanan pokok\nCukup\nGizi seimbang itu apa si ya\nContoh\nCoba\nApaya\nItu kailan\nAku tahu\nKalo ini\nItu bayam\nRiko betul\nPakcoy\nItu suka\nKacang hijau\nIni semua contoh\nTumbuh kita semuharus halal dan', '2026-10-27 14:30:28', 1),
(6, 'energen kini \nlebih\ndengansus asli newzeland dan vitamin\nsarapan pagi lebih\nminum saja ', '2026-10-27 13:23:55', 1),
(7, 'sejak kita tidur kemabli\n', '2026-10-27 13:23:06', 1),
(8, 'halo obat makan bangsa mendorong kami terbaik masyarakat\nterkait makanan aman\nhak setap\nnamun edukasi\nselalu mudh yang jangkau\nlebih dari inovasi yang menghadirkan dan makanan\nmelalui masyarakat terhadap\nbahan bahan yellow penguji\nkesempatan informasi dan terkait\ndi sekolah bykan pengujian\nserta mengawal anak bangsa', '2026-10-27 13:22:22', 1),
(9, 'udah pakai skin care, hair care, tapi hasilnya tetap hanya luar saja vitamin protein oleh tubuh air putih 18 hari seimbang intensive pirin pokok mengandung seperti ikan dan kacang kacangan berdasarkan manusia berbeda wanita 90 tahun kalori per hari 9 tahun per hari 50 sampai di atas seribu da 19 sampai butuhkan ', '2026-10-26 22:22:01', 1);
UNLOCK TABLES;

-- --------------------------------------------------------
-- Table structure for `study_videos`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `study_videos`;
CREATE TABLE `study_videos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `youtube_id` varchar(50) NOT NULL,
  `script` text NOT NULL,
  `created_at` datetime NOT NULL,
  `language` varchar(50) NOT NULL DEFAULT '영어',
  `owner_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_study_videos_owner` (`owner_id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dumping data for table `study_videos` (11 rows)
LOCK TABLES `study_videos` WRITE;
INSERT INTO `study_videos` (`id`, `title`, `youtube_id`, `script`, `created_at`, `language`, `owner_id`) VALUES
(1, 'Madu TJ', 'CqCKZcLl0Yo', '0:000초halo\n0:000초[Musik]\n0:044초halo kembali lagi dengan kita video kali ini kita akan memberi tahu kalian semua apa\n0:1414초aja ya macam-macam varian rasa madu DC dan manfaatnya yuk langsung aja kita ke\n0:2020초videonya jadi madu TJ ini diproduksi oleh lebah\n0:2828초pagi yang fresh dan dipanen saat sudah matang\n0:3232초[Musik]\n0:3333초agensi ini diproses dengan standart formasi dan tentunya telah mendapatkan sertifikasi halal MUI\n0:4242초staf lulus uji SNI madu TJ ini diproduksi secara higienis\n0:5050초dengan teknologi modern dan dikemas dalam botol flip subscribe dan dilengkapi tutup anti tumpah kece log\n1:001분Hai\n1:021분 2초[Musik]\n1:071분 7초King4D lama ya Sekarang kita akan membahas kira-kira apa aja ya varian rasa dari vdj ini\n1:151분 15초hai hai the foreign rasa yang pertama yaitu madu\n1:241분 24초murni Korean ini dijamin 100% madu pilihan yang dipanen saat merdu matang sehingga kualitas terjamin\n1:321분 32초madu TJ murni kaya akan vitamin mineral dan enzim yang lengkap sangat baik untuk\n1:391분 39초kesehatan menjaga stamina tubuh agar tidak mudah sakit\n1:451분 45초varian yang kedua menyebut DJ lemon pada varian ini pastinya menggunakan 100%\n1:531분 53초madu yang asli tetapi mengandung ekstrak lemon dan Mandarin orange sehingga mempunyai\n2:002분khasiat istimewa madu TJ ini sangat baik untuk mereka yang aktif karena membutuhkan stamina tubuh yang ekstra\n2:092분 9초jadi mencuci ini bisa memperkuat daya tahan tubuh sehingga tidak mudah sakit loh\n2:152분 15초varian yang ketiga nyentuh madu kurma perpaduan alami dari kurma asli Arab dan\n2:222분 22초kebaikan ladu saya akan vitamin mineral dan asam amino mestinya bisa bermanfaat untuk menemui\n2:312분 31초fungsi meningkatkan daya tahan tubuh dan mempercepat penyembuhan saat sakit\n2:372분 37초varian yang keempat madu TJ jahe merah mint Aduh decu cahaya merah mini memberikan kehangatan badan Membantu\n2:462분 46초meredakan gejala perut kembung mual sakit perut juga bisa meredakan gejala masuk angin\n2:542분 54초varian kelima make DC panas dalam madu TJ panas dalam ini merupakan madu\n3:013분 1초pilihan dengan kombinasi ekstrak Hai untuk membantu meredakan gejala\n3:083분 8초panas dalam seperti sariawan bibir pecah-pecah tenggorokan kering serta melegakan\n3:153분 15초tenggorokan Nah itu tadi macam-macam varian rasa dan manfaat madu TJ semoga informasi yang\n3:243분 24초kita sampaikan bisa bermanfaat ya jangan lupa subscribe bye bye\n3:333분 33초Hi Ho\n3:353분 35초[Musik]', '2026-10-26 20:59:38', 'ID', 1),
(2, 'Video Promosi Kesehatan ''Pedoman Gizi Seimbang''', 'gx3ZKFb7108', '0:000초Hai\n0:000초[Musik]\n0:066초video promosi kesehatan pedoman gizi seimbang isi piringku\n0:1111초[Musik]\n0:1515초Hai semua Tahukah kamu slogan gizi terbaru\n0:2323초masih ingat dengan slogan 4 sehat 5 sempurna konsep makanan 4 sehat 5 sempurna saat\n0:3131초ini sudah tidak digunakan sebagai rujukan pola makan sehat karena konsep makanan 4 sehat 5 sempurna tidak sesuai\n0:3838초lagi dengan perkembangan ilmu dan permasalahan gizi saat ini Nah sekarang telah disempurnakan menjadi pedoman gizi\n0:4646초seimbang dengan slogan kerennya isi piringku Yuk kita kenali Apa itu isi piringku\n0:5656초panduan gizi ringkuh adalah bagian dari pedoman seimbang atau PGS yang dikampanyekan Kementerian Kesehatan\n1:041분 4초sejak 2017 berbeda dengan 4sehat 5sempurna konsepsi biringku tak hanya\n1:111분 11초menekankan pada apa saja makanan untuk anak sehat yang penting dikonsumsi melainkan juga jumlah porsinya dalam\n1:191분 19초satu piring untuk sekali makan pertama terdiri dari makanan pokok sebagai asupan karbohidrat yang berfungsi untuk\n1:271분 27초sumber energi utama bagi tubuh aneka makanan pokok itu seperti beras kentang\n1:361분 36초gandum jagung ubi singkong dan sagu\n1:441분 44초[Musik]\n1:451분 45초porsi makanan pokok yang ideal untuk anak dalam sajian satu kali makan sesuai dengan isi piringku adalah 2/3 piring\n1:541분 54초atau 35 persen yang juga setara dengan 5 sampai 6 sendok makan nasi atau roti tawar satu lembar yang kedua\n2:032분 3초adalah lauk-pauk asupan protein bermanfaat membantu kecukupan kalori yang dibutuhkan untuk pertumbuhan tinggi\n2:122분 12초dan berat badan serta berperan dalam pembentukan sel-sel tubuh tulang dan juga otot anak terdapat dua jenis\n2:212분 21초protein yaitu protein hewani seperti daging telur ikan\n2:292분 29초hingga makanan laut serta protein nabati seperti tempe tahu\n2:372분 37초kacang-kacangan dan biji-bijian porsi lauk pauk dalam piring anak yang sesuai dengan panduan gizi diringku\n2:462분 46초adalah 35 persen untuk protein hewani setengah potong ayam ukuran sedang atau\n2:532분 53초telur ayam kampung satu butir Sedangkan untuk protein nabati bisa mengkonsumsi satu potong kecil tahu atau tempe atau\n3:033분 3초satu mangkuk kecil bubur kacang hijau ada satu sumber protein lain yang bukan termasuk lauk-pauk tapi bisa menjadi\n3:113분 11초tambahan dan sumber asupan protein yang disukai oleh anak yaitu protein susu\n3:183분 18초yang ketiga adalah sayuran seperti kangkung bayam brokoli\n3:273분 27초buncis terong wortel paprika dan sayuran\n3:353분 35초lainnya bisa dijadikan sumber serat vitamin A C dan mineral\n3:433분 43초dengan bantuan yang dianjurkan untuk mengisi 2/3 bagiannya dengan sayuran bisa dikonsumsi mentah ditumis dikukus\n3:533분 53초atau direbus namun memasaknya jangan terlalu matang ya supaya nutrisi dalam Hai tidak hilang\n4:014분 1초terakhir jangan lupa tambahkan buah ya buah sebagai sumber vitamin sangat\n4:084분 8초penting untuk melengkapi kebutuhan serat air vitamin mineral pada anak isi 1/3\n4:164분 16초bagian piring yang tersisa dengan buah seperti pisang semangka melon jeruk apel\n4:254분 25초mangga kiwi strawberry dan lainnya dilengkapi dengan Minum air mineral\n4:344분 34초minimal 8 gelas sehari aktivitas fisik 30 menit perhari dan jangan lupa Cuci tangan pakai sabun di\n4:434분 43초air mengalir setiap setelah selesai beraktivitas ya ayo penuhi gizi anak sesuai dengan\n4:514분 51초kebutuhannya melalui pedoman gizi seimbang isi piringku supaya anak-anak tumbuh sehat tinggi SD cerdas\n5:015분 1초[Musik]', '2026-10-26 21:29:14', 'ID', 1),
(3, 'Pentingnya Makan Gizi Seimbang Untuk Anak-anak | MBG', 'xazPCFZyC80', '0:00\n[Musik]\n0:15\nBunda, kenapa Rico?\n0:19\nAku lapar, Bunda. Sabar Rico.\n0:26\nBunda,\n0:28\nada apa, Ayah?\n0:30\nAyah lapar nih. Ini Bunda lagi mau masak\n0:34\nkok, Cie. Ayah lapar juga ya.\n0:41\nIya, Nak. Padahal tadi Rico kelihatan\n0:43\nlesu loh. Eh, sekarang malah bisa godain\n0:46\nAyah.\n0:48\nMaaf, Ayah.\n0:51\nBunda mau masak apa, Bunda? Mau masak\n0:54\nsayur. Mau masak ya.\n0:58\nRico enggak suka makan sayur.\n1:02\nRico lebih suka ayam goreng. Wah,\n1:05\npadahal makan sayur itu penting loh,\n1:08\nKyo. Betul. Selain makanan pokok, tubuh\n1:11\nkita juga butuh sayur, lauk, ditambah\n1:14\nbuah. Biar kebutuhan gizi Rico cukup,\n1:17\nmakanya kita harus makan makanan bergizi\n1:20\nseimbang.\n1:22\nGizi seimbang itu apa sih? Ya,\n1:26\ngizi seimbang itu yang dibutuhkan Rico\n1:28\nuntuk tumbuh sehat. Nah, Rico mau tahu\n1:32\ncontoh makanan yang bergizi. Coba tebak\n1:34\nya.\n1:36\nMmm, apa ya? Itu kelor. Hah? Kok kakak\n1:42\ntahu? Iya dong. Kan ada di halaman.\n1:46\nKakulan. Betul. Kalau ini itu mm\n1:52\nitu bayam\n1:54\nRiko. Betul. Kalau ini itu Pak Cooy Ki\n2:01\nBunda. Betul. Kalau ini itu sih kesukaan\n2:04\nayah. Ubi celembu. Wah ayah bener. Nah\n2:10\nkalau ini ah itu sih gampang. Kacang\n2:14\nhijau.\n2:16\nRiko, betul lagi. Ini semua contoh\n2:18\nmakanan yang mengandung vitamin dan\n2:20\nmineral. Dan masih banyak lagi bahan\n2:23\npangan masa depan yang bisa mencukupi\n2:25\nkebutuhan gizi tumbuh sesuai untuk Rico\n2:27\ndan kita semua. Yang paling penting\n2:30\nmakanan itu harus halal dan thayib.\n2:33\nYeah.', '2026-10-26 22:05:10', 'ID', 1),
(4, 'Makan Sehat Bergizi Anak Usia Dini', 'joYtu0WL3po', '0:044초Setiap pagi di sekolah ada semangat baru. Anak-anak datang dengan tawa, siap belajar, dan tumbuh sehat. Semua dimulai dari [musik] makanan bergizi.\n0:1515초Program makan bergizi gratis hadir untuk memastikan setiap anak mendapat asupan gizi seimbang [musik] agar tumbuh sehat, cerdas, dan bahagia.\n0:2424초Selamat pagi, Bu Bunga. Wah, hari ini menunya apa ya? Pagi, Pak Musa. Hari ini\n0:3232초ikan goreng, sayur bayam, dan buah semangka, Pak. Lengkap gizi seimbangnya.\n0:4040초Kok ayamnya enggak ada, ya? [musik] Bu Bunga, kenapa kok makanannya harus\n0:4949초sayur dan buah? Aku kan suka ayam aja.\n0:5454초Sayur dan buah penting, Aa, supaya tubuhmu kuat dan tidak mudah sakit.\n1:011분 1초Betul Ava. Kalau kamu makan seimbang, kamu [musik] bisa tumbah tinggi dan pintar.\n1:071분 7초Kenapa harus ikan? Karena ikan itu baik untuk mata, otak, dan tubuh kita. Selain\n1:161분 16초itu, sayur dan buah bagus untuk tubuh, bikin kita sehat dan kuat. Sebelum anak-anak makan, sekolah harus siap. Ada\n1:241분 24초[musik] tempat cuci tangan, alat ukur berat badan, tempat sampah tertutup, dan pengecekan [musik] makanan dari segi warna, aroma, tekstur, dan rasa.\n1:351분 35초Semuanya harus bersih dan aman. Semua [musik] sudah siap, Pak Musa?\n1:431분 43초Bagus. Kita mulai makan dengan semangat dan penuh rasa syukur, ya.\n1:551분 55초Nah, sebelum makan apa yang harus kita lakukan? Cuci tangan dulu, Pak.\n2:032분 3초Pintar semua. Yuk, makan dengan gembira.\n2:082분 8초Makan bersama bukan hanya soal makanan, [musik] tapi juga pembelajaran tentang kebersihan, disiplin, dan rasa syukur.\n2:162분 16초Setelah makan, [musik] sekolah tetap punya tugas mengevaluasi. mencatat laporan dan menjaga kebersihan lingkungan.\n2:262분 26초Terima kasih, Pak Guru dan Bu Guru. Hari ini aku senang [musik] sekali dan lebih semangat untuk belajar.\n2:342분 34초Sudah selesai semua, Pak Musa. Anak-anak hari ini lahap sekali. [musik] Itu tandanya mereka bahagia dan sehat.\n2:422분 42초Terima kasih, Bu Bunga.\n2:442분 44초Dari satu piring bergizi tumbuh semangat belajar dan masa depan bangsa. Mari bersama wujudkan Indonesia yang sehat\n2:522분 52초dan cerdas. [musik]\n\n동영상 시간 동기화', '2026-10-26 22:06:38', 'ID', 1),
(5, 'PETUALANGAN SI KECIL & MAKANAN SEHAT', 'aQ2nMcqXRcE', '0:00\n[Musik]\n0:27\nasalamualaikum warahmatullahi\n0:29\nwabarakatuh\n0:30\nSelamat pagi adik-adik yang ceria saat\n0:33\nini kakak akan bercerita mengenai\n0:36\nmanfaat makanan terutama sayuran dan\n0:39\nbuah-buahan di channel gizides ini akan\n0:42\nmakin banyak cerita untuk adik-adik\n0:45\nmengenai makanan dan gizi mari kita\n0:47\nmulai ceritanya cerita saat ini berjudul\n0:51\npetualangan si kecil dan makanan sehat\n0:55\ndi sebuah desa kecil yang dikelili sawah\n0:58\nhijau hiduplah or anak\n1:02\nber anak yanger dan\n1:06\nberetualangu\n1:13\ndiius\n1:17\nyangak\n1:19\nyangsan\n1:22\ndan-an si kam\n1:30\ndatang untuk memberitahumu tentang\n1:32\nkekuatan luar biasa dari makanan sehat\n1:35\njawab pahlawan tersebut dengan suara\n1:38\nceria pahlawan makanan sehat mengajak\n1:41\nDika untuk melakukan petualangan ke\n1:44\ndunia makanan sehat mereka pertama-tama\n1:47\nmengunjungi sebuah taman yang dipenuhi\n1:50\ndengan sayuran berwarna-warni seperti\n1:53\nwortel oran brokoli hijau dan tomat\n1:56\nmerah cerah ini adalah sayuran yang\n2:00\npenuh dengan vitamin dan mineral yang\n2:02\nakan membuat tubuhmu lebih kuat dan\n2:04\nsehat kata pahlawan makanan sehat sambil\n2:08\nmemetik wortel dari tanah Dika mencoba\n2:11\nmemakannya dan dia merasa lebih\n2:14\nberenergi Wah rasanya enak sekali seru\n2:18\nDika dengan semangat Selain itu\n2:21\nbuah-buahan seperti apel jeruk dan\n2:24\npisang juga sangat baik untuk tubuhmu\n2:27\ntambah pahlawan makanan sehat\n2:30\nmenukkan pohon buah yang Berbah lebatah\n2:34\nmenikmati sayuran dan buah-buahan di\n2:37\ndiaj ke\n2:40\nseb J\n2:43\nyang Sal\n2:58\ndanun aku bisa menjadi lebih pintar dan\n3:02\nkuat serunya Mereka kemudian melanjutkan\n3:05\nperjalanan ke sebuah ladang gandum\n3:08\nTempat roti dan sereal sehat\n3:10\ndiproduksi karbohidrat dari gandum\n3:13\nmemberi energi yang cukup untuk tubuhmu\n3:16\nagar tetap aktif sepanjang hari jelas\n3:19\npahlawan makanan sehat pahlawan makanan\n3:23\nsehat Mawa seb\n3:26\npas Diany makan\n4:00\ntetap kuat dan\n4:01\nsehat setelah perjalanan yang\n4:03\nmenyenangkan Dika kembali ke rumah\n4:06\ndengan penuh semangat dia berjanji untuk\n4:09\nmakan lebih banyak makanan sehat setiap\n4:12\nhari dan berbagi pengetahuannya dengan\n4:15\nteman temannya Terima kasih pahlawan\n4:19\nmakanan sehat Aku sekarang tahu betapa\n4:22\npentingnya makanan yang sehat untuk\n4:25\ntubuh kita\n4:27\nujambil Melambaikan tangan ke ke arah\n4:30\npahlawan tersebut pahlawan makanan sehat\n4:33\ntersenyum ingat di makan makanan yang\n4:37\nsehat Itu pting untuk tbuh besar dan\n4:40\nkuat selalu pilih makanan yang memberi\n4:43\nmanfaat untuk\n4:45\ntubuhmu dengan pengetahuan baru yang\n4:48\ndidapat di mulai memilih makanan yang\n4:51\nsehat dan merasa lebih bertenaga harinya\n4:55\ndia tahu bahwa dengan makanh\n4:59\nbisa menjadi anak yang lebih kuat lebih\n5:03\npintar dan lebih bahagia demikian cerita\n5:07\nKakak mengenai petualangan si kecil dan\n5:11\nmakanan sehat wabillahi Taufik W Hidayah\n5:17\nwasalamualaikum\n5:18\nwarahmatullahi\n5:26\n[Musik]\n5:28\nwabarakatuh foreign\n5:35\n[Musik]', '2026-10-26 22:08:18', 'ID', 1),
(6, 'IKLAN ENERGEN SEREAL & SUSU (2022)', '31KfO4bi3Ho', '0:022초two tertutup\n0:1111초Energen kini isi lebih banyak Lebih banyak susu lebih banyak sereal lebih banyak vitamin dengan sesuai sini usilan\n0:2020초bukan sembarang susu serial kaya serat baik untuk pencernaan dan vitamin untuk daya tahan tubuh sarapan pagi Wow lebih\n0:2828초banyak serealnya lapar sore lapar malam minum saja Energen lebih enak lebih kenyal minum\n0:3737초Energen sereal makanan bergizi di\n0:4444초[Musik]', '2026-10-26 22:10:03', 'ID', 1),
(7, 'Label yang Lebih Baik untuk Masa Depan yang Lebih Sehat', 'mTWWrWkFGCw', '0:000초[musik]\n0:022초Sejak kita bangun tidur hingga kita pergi tidur kembali, kita dikelilingi oleh iklan makanan. Iklan-iklan itu ada\n0:1010초di transportasi umum, di papan reklame, di televisi dan radio, dan [musik] terutama di media sosial kita. Di mana\n0:1818초perusahaan menggunakan teknik-teknik khusus untuk membuat kita dan anak-anak kita membeli produk mereka yang seringki\n0:2626초merupakan makanan ultraproses yang tinggi gula. lemak trans dan [musik] garam.\n0:3434초Dalam sebuah studi tahun 2025, dari 295 iklan yang berasal dari 20 merek makanan\n0:4141초dan minuman terkemuka di media sosial, 85% di antaranya mempromosikan setidaknya satu produk yang tidak layak [musik] dikonsumsi oleh anak-anak.\n0:5252초Iklan-iklan ini menggoda, [musik] penuh warna, dan ada di mana-mana. dan semuanya turut mendorong meningkatnya\n0:5959초pola makan [musik] tidak sehat serta penyakit yang berkaitan dengan pola makan seperti hipertensi, penyakit jantung, dan diabetes.\n1:091분 9초Saat kita berbelanja, apa yang sebenarnya disampaikan oleh label pada kemasan makanan kepada kita? Untuk\n1:161분 16초membantu kita memahami apa yang kita makan, negara-negara di seluruh dunia telah mewajibkan pencantuman label pada\n1:231분 23초bagian depan kemasan. Label ini memudahkan kita untuk [musik] membandingkan produk makanan dan membuat pilihan yang lebih sehat untuk keluarga dan diri kita sendiri.\n1:361분 36초Namun dengan begitu banyak jenis label depan kemasan yang ada di dunia, mana yang paling efektif? Untuk menjawab\n1:441분 44초pertanyaan itu, UNICEF bersama Kementerian Kesehatan dan Badan Pengawas Obat dan Makanan [musik] melakukan studi skala besar pertama di Indonesia tentang pelabelan pangan.\n1:551분 55초Lebih dari 4.000 peserta diminta membandingkan produk makanan menggunakan berbagai sistem pelabelan.\n2:042분 4초Dibandingkan dengan panel informasi gizi yang mencantumkan [musik] panduan asupan harian, semua label interpretatif yang\n2:112분 11초diuji membantu partisipan membuat pilihan yang lebih sehat.\n2:172분 17초Ada kabar baik. Pada 2026, Indonesia memperkenalkan sistem nutri level.\n2:242분 24초Seperti label-label yang unggul dalam studi tersebut. Ini adalah sistem yang mudah ditafsirkan dengan memberikan\n2:312분 31초nilai huruf dari A hingga D pada produk makanan berdasarkan kandungan gula, garam, [musik] dan lemaknya.\n2:412분 41초Nutri Level memiliki potensi untuk melangkah lebih jauh. Nilai hurufnya bisa menjadi [musik] dasar bagi perubahan kebijakan yang kuat dengan\n2:492분 49초membatasi pemasaran produk-produk\n2:502분 50초[musik]\n2:512분 51초dengan peringkat terendah dan menjauhkannya dari ruang-ruang tempat anak-anak belajar dan bertumbuh seperti\n2:582분 58초sekolah. Industri [musik] makanan telah menghabiskan puluhan tahun membuat makanan tidak sehat tampak layak [musik]\n3:053분 5초dikonsumsi. Tetapi kini kita memiliki alat yang sederhana dan mudah digunakan yang memberdayakan kita untuk membuat\n3:133분 13초pilihan sendiri tentang apa yang [musik] kita makan. Label yang lebih baik berarti pilihan yang lebih baik.\n3:233분 23초Dan pilihan [musik] yang lebih baik berarti anak-anak yang lebih sehat, keluarga yang lebih sehat, dan Indonesia [musik] yang lebih sehat.\n3:363분 36초[musik]\n3:383분 38초Yeah.', '2026-10-26 22:10:51', 'ID', 1),
(8, 'Inovasi BPOM Sofifi Baronda', '-5ybbS8hJNQ', '0:088초Halo sobat Bepom, garda terdepan pengawasan [musik] obat dan makanan.\n0:1313초Semangat melayani bangsa mendorong kami terus bergerak untuk memberikan yang terbaik menjangkau [musik] masyarakat.\n0:2020초Kini BPOM Sofivi Baronda beri layanan terkait obat dan makanan aman. Keamanan obat dan makanan adalah hak setiap\n0:2929초masyarakat. Namun akses terhadap informasi, edukasi, dan layanan pengujian tidak selalu mudah dijangkau.\n0:3737초Karena itu, kami melihat sebuah kebutuhan sederhana. Kini layanan BPOM kami bawah lebih dekat dengan\n0:4444초masyarakat. [musik] Dari pertanyaan itulah baronda bergerak.\n0:4949초BPOM Sofivi Baronda merupakan inovasi pelayanan publik Balai Pom di [musik] Sofivi yang menghadirkan layanan\n0:5656초pengawasan obat dan makanan secara langsung ke tengah masyarakat. Melalui mobil laboratorium keliling, [musik]\n1:041분 4초masyarakat dapat memperoleh layanan uji cepat secara gratis terhadap pangan yang diduga mengandung bahan-bahan berbahaya\n1:121분 12초seperti formalin, boraks, rodamin B, dan metanil [musik] yellow. Baronda bukan hanya tentang menguji, tapi juga\n1:201분 20초melindungi. Setiap layanan adalah kesempatan untuk memberikan pengetahuan.\n1:261분 26초Melalui Baronda, masyarakat bisa mendapatkan informasi dan edukasi terkait penggunaan obat serta makanan\n1:331분 33초yang aman. Di sekolah, Baronda hadir bukan sekedar [musik] membawa alat pengujian. Kami mencoba menghadirkan\n1:411분 41초pengetahuan serta mengawal keamanan pangan bagi [musik] anak bangsa.\n1:481분 48초Sekolah berkomitmen menghadirkan pangan jajanan yang aman bagi seluruh murid. Murid sehat Indonesia kuat.\n1:571분 57초Di [musik] pasar, Baronda hadir melakukan pengawasan lebih dekat kepada masyarakat untuk pangan yang lebih aman.\n2:092분 9초Asalamualaikum warahmatullahi wabarakatuh. Subajo. Saya Kepala Dinas Perindustrian dan Perdagangan Kota\n2:172분 17초Ternate berkomitmen melaksanakan dan mendukung replikasi inovasi baronda atau\n2:252분 25초beri layanan terkait obat dan makanan yang dilaksanakan oleh Balai POM di Sovivi pada pasar-pasar di Kota Ternate.\n2:362분 36초Pelaksanaan replikasi di pasar barito dan pasar dupa-dua telah meningkatkan kesadaran pedagang dalam menjaga\n2:442분 44초keamanan pangan. Ini menjadi langkah positif untuk menciptakan pasar yang lebih aman, sehat, dan nyaman bagi masyarakat. Terima kasih.\n2:542분 54초Wasalamualaikum warahmatullahi wabarakatuh. Subajo.\n2:582분 58초Kini baronda direplikasi oleh Dinas Perindustrian dan Perdagangan Kota Ternate di Pasar Barito Bahari Berkesan dan Pasar Dufauva.\n3:123분 12초Perjalanan Baronda belum selesai. Kami melihat Baronda bukan hanya sebagai mobil laboratorium keliling. Baronda\n3:203분 20초akan menjadi mall pelayanan publik keliling. Sebuah layanan yang bergerak dari satu tempat ke tempat lain, [musik] mendekatkan layanan, menyederhanakan\n3:293분 29초akses, dan menghadirkan BPOM di tengah masyarakat. Karena pelayanan publik bukan tentang seberapa jauh masyarakat\n3:363분 36초datang untuk mendapatkan layanan, tapi seberapa jauh kita mampu bergerak untuk melayani masyarakat.', '2026-10-26 22:12:25', 'ID', 1),
(9, 'ILM Edukasi Gizi Seimbang', '1bcI39ssaaw', '0:00\nudah pakai Skincare body care hair care\n0:04\ntapi hasilnya tetap nihil\n0:06\ngirls merawat tubuh dan wajah tidak\n0:09\ncukup hanya dari luar saja kamu juga\n0:12\nperlu mengkonsumsi makanan yang\n0:14\nmengandung vitamin protein serat dan\n0:17\nlemak yang dibutuhkan oleh tubuh dan\n0:20\njuga penuhi kebutuhan nutrisi kulitmu\n0:22\ndengan minum air putih 8 gelas sehari\n0:26\nSudahkah kamu memiliki gizi yang\n0:28\nseimbang untuk tubuh kamu yuk intip-tip\n0:31\nsehat dari Kemenkes\n0:33\nisi setengah piringmu dengan makanan\n0:36\npokok dan lauk pauk yang mengandung\n0:38\nprotein nabati dan hewani seperti ikan\n0:41\ndan kacang-kacangan kemudian setengahnya\n0:44\nlagi kamu isi dengan makanan berserat\n0:46\nseperti sayur bayam wortel dan pisang\n0:49\n[Musik]\n0:51\nberdasarkan jenis kelamin dan usia\n0:53\nkebutuhan nutrisi dalam tubuh manusia\n0:56\nitu berbeda-beda loh contohnya kebutuhan\n0:59\nkalori wanita 19 sampai dengan 29 tahun\n1:04\n2250 kalori per hari kemudian wanita\n1:07\nberusia 30 sampai dengan 49 tahun\n1:11\n2150 kalori per hari lalu wanita berusia\n1:15\n50 sampai dengan 64 tahun\n1:18\n1900 kalori per hari dan wanita berusia\n1:21\ndi atas 65 tahun membutuhkan\n1:24\n1550 kalori per hari\n1:26\nNah untuk pria berusia 19 sampai dengan\n1:30\n29 tahun membutuhkan kalori sebanyak\n1:34\n2.725 kalori per hari kemudian 30 sampai\n1:39\ndengan 49 tahun\n1:42\n2625 kalori perhari 50 sampai dengan 64\n1:46\ntahun\n1:48\n2325 kalori per hari dan pria Beru Sia\n1:51\ndi atas 65 tahun membutuhkan kalori\n1:54\nsebesar 1900 kalori per hari\n1:58\nso girls mulai konsumsi makanan dengan\n2:01\ngizi yang seimbang ya kurangi\n2:03\nmengkonsumsi makanan cepat saji Ayo mari\n2:06\nkita hidup sehat dari piring kita\n2:08\naktivitas fisik dan PHBS mulai dari saat\n2:11\nini\n2:19\n[Musik]', '2026-10-26 22:13:36', 'ID', 1),
(11, 'CONTOH SAMBUTAN SINGKAT - BELAJAR SAMBUTAN', 'ti3N6EzA_kY', '0:000초hai hai Hai assalamualaikum warahmatullah\n0:099초wabarakatuh bersyukur kepada Allah dengan ucapan Alhamdulillah bershalawat\n0:1717초kepada Baginda Nabi dengan ucapan allahummasollialamuhammad yang saya\n0:2424초hormati segenap tokoh masyarakat para pejabat muslimin serta muslimat mohon\n0:3232초maaf tidak bisa saya Sebutkan satu persatu tapi Insyaallah tidak mengurangi\n0:3838초rasa hormat hadirin yang berbahagia saya mewakili panitia penyelenggara\n0:4545초mengucapkan terima kasih yang sebesar-besarnya kepada seluruh pihak yang ikut membantu mensukseskan acara\n0:5353초ini semoga semuanya dibalas dengan sebaik-baiknya balasan menjadi sebab\n1:001분datangnya kebaikan dan keberkahan dan kami juga mohon maaf sebesar-besarnya karena tentu\n1:071분 7초ada banyak kekurangan pada acara ini tapi Insyaallah segala kekurangan tidak kami buat dengan sengaja karena kami\n1:161분 16초panitia dari awal sudah berniat membuat acara terbaik yang kami bisa agar Bapak\n1:231분 23초Ibu semua bisa senang dan bahagia tapi apalah daya kami Manusia tempatnya salah\n1:301분 30초dan juga dosa bapak ibu hadirin yang berbahagia ada pantun bunyinya seperti\n1:371분 37초ini Bapak Ibu ikan sepat ikan gabus lebih cepat lebih bagus jadi Cukup\n1:431분 43초sekian sambutan saya Bapak Ibu pergi ke sawah menanam padi salah dan khilaf mohon dimaklumi Wassalamualaikum\n1:521분 52초warahmatullah wabarakatuh', '2026-10-29 16:19:13', 'ID', 1),
(12, 'Iklan Produk Makanan 30 detik', '7u2cRtL6sZo', '0:022초pagi-pagi gini enak lagi kalau bikin\n0:099초[Musik]\n0:1010초kopi tapi kayaknya kurang deh kalau cuma kopi aja\n0:1515초[Musik]\n0:1818초ah Nah ini nih cipis Kik pisang berkitas tinggi yang cocok untuk dijadikan cilan\n0:2626초pendamping cipis keripiknya bikin asik', '2026-10-29 16:20:42', 'ID', 1);
UNLOCK TABLES;

-- --------------------------------------------------------
-- Table structure for `utility_records`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `utility_records`;
CREATE TABLE `utility_records` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `billing_month` char(7) NOT NULL,
  `electricity_usage` decimal(10,2) NOT NULL DEFAULT 0.00,
  `electricity_fee` decimal(18,2) NOT NULL DEFAULT 0.00,
  `water_usage` decimal(10,2) NOT NULL DEFAULT 0.00,
  `water_fee` decimal(18,2) NOT NULL DEFAULT 0.00,
  `telecom_fee` decimal(18,2) NOT NULL DEFAULT 0.00,
  `gas_fee` decimal(18,2) NOT NULL DEFAULT 0.00,
  `other_fee` decimal(18,2) NOT NULL DEFAULT 0.00,
  `total_fee` decimal(18,2) NOT NULL DEFAULT 0.00,
  `memo` text NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  `owner_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_utility_month` (`owner_id`,`billing_month`),
  KEY `idx_utility_records_owner` (`owner_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dumping data for table `utility_records` (2 rows)
LOCK TABLES `utility_records` WRITE;
INSERT INTO `utility_records` (`id`, `billing_month`, `electricity_usage`, `electricity_fee`, `water_usage`, `water_fee`, `telecom_fee`, `gas_fee`, `other_fee`, `total_fee`, `memo`, `created_at`, `updated_at`, `owner_id`) VALUES
(1, '2025-01', '0.00', '29990.00', '0.00', '11000.00', '0.00', '171640.00', '0.00', '212630.00', '수도세는 2개월마다 3층에 송금', '2026-10-27 16:22:04', '2026-10-27 16:23:36', 1),
(2, '2025-02', '0.00', '0.00', '0.00', '0.00', '0.00', '244860.00', '0.00', '244860.00', '', '2026-10-27 16:23:19', '2026-10-27 16:23:19', 1);
UNLOCK TABLES;

-- --------------------------------------------------------
-- Table structure for `vocab_list`
-- --------------------------------------------------------
DROP TABLE IF EXISTS `vocab_list`;
CREATE TABLE `vocab_list` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `word` varchar(100) NOT NULL,
  `meaning` varchar(255) NOT NULL,
  `created_at` datetime NOT NULL,
  `video_id` int(11) DEFAULT NULL,
  `owner_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_vocab_list_owner` (`owner_id`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dumping data for table `vocab_list` (37 rows)
LOCK TABLES `vocab_list` WRITE;
INSERT INTO `vocab_list` (`id`, `word`, `meaning`, `created_at`, `video_id`, `owner_id`) VALUES
(1, 'sekarang', '지금', '2026-10-27 16:38:38', 3, 1),
(2, 'seimbang untuk tubuh kamu yuk intip', 'tip', '2026-10-27 18:36:28', 9, 1),
(3, 'hasilnya', '결과', '2026-10-27 18:36:28', 9, 1),
(4, 'tetap', '아직', '2026-10-27 18:36:28', 9, 1),
(5, 'nihil', '무', '2026-10-27 18:36:28', 9, 1),
(6, 'merawat', '간호사', '2026-10-27 18:36:28', 9, 1),
(7, 'tubuh', '몸', '2026-10-27 18:36:28', 9, 1),
(8, 'wajah', '얼굴', '2026-10-27 18:36:28', 9, 1),
(9, 'tidak', '아니다, 안 하다', '2026-10-27 18:36:28', 9, 1),
(10, 'luar', '밖의', '2026-10-27 18:36:28', 9, 1),
(11, 'saja', '오직, 그냥', '2026-10-27 18:36:28', 9, 1),
(12, 'mengkonsumsi', '소비하다', '2026-10-27 18:36:28', 9, 1),
(13, 'mengandung', '포함하다', '2026-10-27 18:36:28', 9, 1),
(14, 'protein', '단백질', '2026-10-27 18:36:28', 9, 1),
(15, 'serat', '섬유', '2026-10-27 18:36:28', 9, 1),
(16, 'sobat', '친구', '2026-10-27 18:38:08', 8, 1),
(17, 'Bepom', '베폼', '2026-10-27 18:38:08', 8, 1),
(18, 'garda', '경비원', '2026-10-27 18:38:08', 8, 1),
(19, 'terdepan', '선두 가장자리', '2026-10-27 18:38:08', 8, 1),
(20, 'pengawasan', '감독', '2026-10-27 18:38:08', 8, 1),
(21, 'Semangat', '영혼', '2026-10-27 18:38:08', 8, 1),
(22, 'melayani', '제공하다', '2026-10-27 18:38:08', 8, 1),
(23, 'bangsa', '국가', '2026-10-27 18:38:08', 8, 1),
(24, 'mendorong', '푸시', '2026-10-27 18:38:08', 8, 1),
(25, 'bergerak', '이동하다', '2026-10-27 18:38:08', 8, 1),
(26, 'memberikan', '주다', '2026-10-27 18:38:08', 8, 1),
(27, 'terbaik', '최상의', '2026-10-27 18:38:08', 8, 1),
(28, 'menjangkau', '도달하다', '2026-10-27 18:38:08', 8, 1),
(29, 'masyarakat', '공공의', '2026-10-27 18:38:08', 8, 1),
(30, 'Kini', '지금', '2026-10-27 18:38:08', 8, 1),
(31, 'BPOM', 'BPOM', '2026-10-27 18:38:08', 8, 1),
(32, 'Sofivi', '소피비', '2026-10-27 18:38:08', 8, 1),
(33, 'Baronda', '바론다', '2026-10-27 18:38:08', 8, 1),
(34, 'layanan', '서비스', '2026-10-27 18:38:08', 8, 1),
(35, 'terkait', '관련된', '2026-10-27 18:38:08', 8, 1),
(36, 'Keamanan', '보안', '2026-10-27 18:38:08', 8, 1),
(37, 'hak', '일', '2026-10-27 18:38:08', 8, 1);
UNLOCK TABLES;

SET FOREIGN_KEY_CHECKS = 1;
