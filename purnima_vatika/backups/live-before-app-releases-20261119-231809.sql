-- MySQL dump 10.13  Distrib 8.4.13, for Linux (aarch64)
--
-- Host: 193.203.184.167    Database: u662998774_purnima_vatika
-- ------------------------------------------------------
-- Server version	11.8.9-MariaDB-log

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `_prisma_migrations`
--

DROP TABLE IF EXISTS `_prisma_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `_prisma_migrations` (
  `id` varchar(36) NOT NULL,
  `checksum` varchar(64) NOT NULL,
  `finished_at` datetime(3) DEFAULT NULL,
  `migration_name` varchar(255) NOT NULL,
  `logs` text DEFAULT NULL,
  `rolled_back_at` datetime(3) DEFAULT NULL,
  `started_at` datetime(3) NOT NULL DEFAULT current_timestamp(3),
  `applied_steps_count` int(10) unsigned NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `_prisma_migrations`
--

LOCK TABLES `_prisma_migrations` WRITE;
/*!40000 ALTER TABLE `_prisma_migrations` DISABLE KEYS */;
INSERT INTO `_prisma_migrations` VALUES ('3783fb5c-5f93-431c-b4cf-9b4abfc9662c','bd9b85ffcfaf9e22fb18b97981dc516e18d41c65d3b81ee4e81b9c3d03b4f278','2026-11-14 17:07:47.643','20261114052011_init',NULL,NULL,'2026-11-14 17:07:46.978',1),('7542158d-5ffd-466b-a981-aa0d44d53230','e93a18ad09b5c20432f0e81e0da96d12a61117889d37e374b6364e2f263e2028','2026-11-14 18:35:12.869','20261114181626_purchase_images',NULL,NULL,'2026-11-14 18:35:12.502',1),('9073ad50-5b26-4836-afb0-6207f140ec47','02134c7e252865c11bec1164b883faf8460735ee31d09712fda2144ba676b759','2026-11-18 16:57:27.835','20261118163631_idempotency_keys',NULL,NULL,'2026-11-18 16:57:27.182',1),('e10fd290-4312-441b-ae04-d8f036521766','6ea84a6e231d1c14c345a0dd0791e66b1ae404c5b24a898a730d1019bef009b8','2026-11-18 17:35:56.677','20261118172145_attendance_daily_supplies',NULL,NULL,'2026-11-18 17:35:56.252',1),('f25fc403-9fa0-4d84-aa7c-63c397585db3','05d1e8374dbc506b1adec715f58adcde0f5d706320f6de5baa0d2ab52df98c56','2026-11-18 16:32:17.135','20261118162354_employee_documents',NULL,NULL,'2026-11-18 16:32:16.652',1);
/*!40000 ALTER TABLE `_prisma_migrations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `attendance`
--

DROP TABLE IF EXISTS `attendance`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `attendance` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `employeeId` int(11) NOT NULL,
  `date` date NOT NULL,
  `status` enum('ABSENT','HALF_DAY') NOT NULL,
  `note` varchar(255) DEFAULT NULL,
  `createdBy` int(11) DEFAULT NULL,
  `createdAt` datetime(3) NOT NULL DEFAULT current_timestamp(3),
  `updatedAt` datetime(3) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `attendance_employeeId_date_key` (`employeeId`,`date`),
  KEY `attendance_date_idx` (`date`),
  CONSTRAINT `attendance_employeeId_fkey` FOREIGN KEY (`employeeId`) REFERENCES `employees` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `attendance`
--

LOCK TABLES `attendance` WRITE;
/*!40000 ALTER TABLE `attendance` DISABLE KEYS */;
INSERT INTO `attendance` VALUES (1,2,'2026-11-17','ABSENT',NULL,1,'2026-11-18 17:39:20.134','2026-11-18 17:39:20.134'),(2,2,'2026-11-16','ABSENT',NULL,1,'2026-11-18 17:39:24.542','2026-11-18 17:39:24.542'),(3,1,'2026-11-16','ABSENT',NULL,1,'2026-11-18 17:39:27.510','2026-11-18 17:39:27.510'),(4,1,'2026-11-17','ABSENT',NULL,1,'2026-11-18 17:39:28.850','2026-11-18 17:39:28.850');
/*!40000 ALTER TABLE `attendance` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `bill_items`
--

DROP TABLE IF EXISTS `bill_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bill_items` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `billId` int(11) NOT NULL,
  `menuItemId` int(11) DEFAULT NULL,
  `name` varchar(120) NOT NULL,
  `quantity` decimal(12,3) NOT NULL,
  `rate` decimal(12,2) NOT NULL,
  `amount` decimal(12,2) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `bill_items_billId_fkey` (`billId`),
  KEY `bill_items_menuItemId_fkey` (`menuItemId`),
  CONSTRAINT `bill_items_billId_fkey` FOREIGN KEY (`billId`) REFERENCES `bills` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `bill_items_menuItemId_fkey` FOREIGN KEY (`menuItemId`) REFERENCES `menu_items` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `bill_items`
--

LOCK TABLES `bill_items` WRITE;
/*!40000 ALTER TABLE `bill_items` DISABLE KEYS */;
INSERT INTO `bill_items` VALUES (1,1,11,'Sav mixture 100',3.000,25.00,75.00),(2,1,13,'Tea',13.000,10.00,130.00),(3,2,1,'Veg Thali',1.000,70.00,70.00),(4,2,7,'Water 1L',1.000,20.00,20.00),(5,2,6,'Watter 0.5L',2.000,10.00,20.00),(6,3,20,'Tadka +Roti',3.000,80.00,240.00),(7,3,14,'seasonal Vegetable plate',1.000,30.00,30.00),(8,3,7,'Water 1L',1.000,20.00,20.00),(9,4,21,'Paneer +Roti',1.000,120.00,120.00),(10,4,18,'Egg Burji (2 egg)',1.000,30.00,30.00);
/*!40000 ALTER TABLE `bill_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `bills`
--

DROP TABLE IF EXISTS `bills`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bills` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `date` date NOT NULL,
  `tableNo` varchar(20) DEFAULT NULL,
  `customerId` int(11) DEFAULT NULL,
  `subtotal` decimal(12,2) NOT NULL,
  `discount` decimal(12,2) NOT NULL DEFAULT 0.00,
  `total` decimal(12,2) NOT NULL,
  `cashAmount` decimal(12,2) NOT NULL DEFAULT 0.00,
  `upiAmount` decimal(12,2) NOT NULL DEFAULT 0.00,
  `notes` varchar(255) DEFAULT NULL,
  `status` enum('ACTIVE','CANCELLED') NOT NULL DEFAULT 'ACTIVE',
  `cancelReason` varchar(255) DEFAULT NULL,
  `createdBy` int(11) DEFAULT NULL,
  `createdAt` datetime(3) NOT NULL DEFAULT current_timestamp(3),
  `updatedAt` datetime(3) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `bills_date_idx` (`date`),
  KEY `bills_customerId_date_idx` (`customerId`,`date`),
  CONSTRAINT `bills_customerId_fkey` FOREIGN KEY (`customerId`) REFERENCES `customers` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `bills`
--

LOCK TABLES `bills` WRITE;
/*!40000 ALTER TABLE `bills` DISABLE KEYS */;
INSERT INTO `bills` VALUES (1,'2026-11-19',NULL,NULL,205.00,0.00,205.00,205.00,0.00,NULL,'ACTIVE',NULL,1,'2026-11-19 14:46:27.324','2026-11-19 14:46:27.324'),(2,'2026-11-19',NULL,NULL,110.00,0.00,110.00,0.00,110.00,NULL,'ACTIVE',NULL,1,'2026-11-19 14:47:33.154','2026-11-19 14:47:33.154'),(3,'2026-11-19',NULL,NULL,290.00,0.00,290.00,0.00,290.00,NULL,'ACTIVE',NULL,1,'2026-11-19 15:08:36.403','2026-11-19 15:08:36.403'),(4,'2026-11-19',NULL,NULL,150.00,0.00,150.00,0.00,150.00,NULL,'ACTIVE',NULL,1,'2026-11-19 15:10:51.168','2026-11-19 15:10:51.168');
/*!40000 ALTER TABLE `bills` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `customers`
--

DROP TABLE IF EXISTS `customers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `customers` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `phone` varchar(15) NOT NULL,
  `name` varchar(120) DEFAULT NULL,
  `birthday` date DEFAULT NULL,
  `anniversary` date DEFAULT NULL,
  `notes` varchar(255) DEFAULT NULL,
  `createdAt` datetime(3) NOT NULL DEFAULT current_timestamp(3),
  `updatedAt` datetime(3) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `customers_phone_key` (`phone`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `customers`
--

LOCK TABLES `customers` WRITE;
/*!40000 ALTER TABLE `customers` DISABLE KEYS */;
/*!40000 ALTER TABLE `customers` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `daily_sales`
--

DROP TABLE IF EXISTS `daily_sales`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `daily_sales` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `date` date NOT NULL,
  `cashAmount` decimal(12,2) NOT NULL DEFAULT 0.00,
  `upiAmount` decimal(12,2) NOT NULL DEFAULT 0.00,
  `notes` varchar(255) DEFAULT NULL,
  `status` enum('ACTIVE','CANCELLED') NOT NULL DEFAULT 'ACTIVE',
  `createdBy` int(11) DEFAULT NULL,
  `createdAt` datetime(3) NOT NULL DEFAULT current_timestamp(3),
  `updatedAt` datetime(3) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `daily_sales_date_idx` (`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `daily_sales`
--

LOCK TABLES `daily_sales` WRITE;
/*!40000 ALTER TABLE `daily_sales` DISABLE KEYS */;
/*!40000 ALTER TABLE `daily_sales` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `daily_supplies`
--

DROP TABLE IF EXISTS `daily_supplies`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `daily_supplies` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `vendorId` int(11) NOT NULL,
  `itemId` int(11) NOT NULL,
  `defaultQty` decimal(12,3) NOT NULL,
  `rate` decimal(12,2) NOT NULL,
  `startDate` date NOT NULL,
  `active` tinyint(1) NOT NULL DEFAULT 1,
  `notes` varchar(255) DEFAULT NULL,
  `createdAt` datetime(3) NOT NULL DEFAULT current_timestamp(3),
  `updatedAt` datetime(3) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `daily_supplies_vendorId_fkey` (`vendorId`),
  KEY `daily_supplies_itemId_fkey` (`itemId`),
  CONSTRAINT `daily_supplies_itemId_fkey` FOREIGN KEY (`itemId`) REFERENCES `items` (`id`) ON UPDATE CASCADE,
  CONSTRAINT `daily_supplies_vendorId_fkey` FOREIGN KEY (`vendorId`) REFERENCES `vendors` (`id`) ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `daily_supplies`
--

LOCK TABLES `daily_supplies` WRITE;
/*!40000 ALTER TABLE `daily_supplies` DISABLE KEYS */;
INSERT INTO `daily_supplies` VALUES (1,3,35,3.000,60.00,'2026-11-01',1,NULL,'2026-11-19 02:12:39.211','2026-11-19 15:49:21.344'),(2,4,61,1.000,4.00,'2026-11-01',1,NULL,'2026-11-19 02:16:44.168','2026-11-19 15:51:03.937');
/*!40000 ALTER TABLE `daily_supplies` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `daily_supply_bills`
--

DROP TABLE IF EXISTS `daily_supply_bills`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `daily_supply_bills` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `supplyId` int(11) NOT NULL,
  `month` varchar(7) NOT NULL,
  `purchaseId` int(11) NOT NULL,
  `createdAt` datetime(3) NOT NULL DEFAULT current_timestamp(3),
  PRIMARY KEY (`id`),
  KEY `daily_supply_bills_supplyId_month_idx` (`supplyId`,`month`),
  CONSTRAINT `daily_supply_bills_supplyId_fkey` FOREIGN KEY (`supplyId`) REFERENCES `daily_supplies` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `daily_supply_bills`
--

LOCK TABLES `daily_supply_bills` WRITE;
/*!40000 ALTER TABLE `daily_supply_bills` DISABLE KEYS */;
/*!40000 ALTER TABLE `daily_supply_bills` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `daily_supply_entries`
--

DROP TABLE IF EXISTS `daily_supply_entries`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `daily_supply_entries` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `supplyId` int(11) NOT NULL,
  `date` date NOT NULL,
  `quantity` decimal(12,3) NOT NULL,
  `note` varchar(255) DEFAULT NULL,
  `createdBy` int(11) DEFAULT NULL,
  `updatedAt` datetime(3) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `daily_supply_entries_supplyId_date_key` (`supplyId`,`date`),
  CONSTRAINT `daily_supply_entries_supplyId_fkey` FOREIGN KEY (`supplyId`) REFERENCES `daily_supplies` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `daily_supply_entries`
--

LOCK TABLES `daily_supply_entries` WRITE;
/*!40000 ALTER TABLE `daily_supply_entries` DISABLE KEYS */;
INSERT INTO `daily_supply_entries` VALUES (1,1,'2026-11-18',2.000,NULL,1,'2026-11-19 15:49:44.896'),(2,1,'2026-11-17',2.000,NULL,1,'2026-11-19 15:49:49.844');
/*!40000 ALTER TABLE `daily_supply_entries` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `employee_advances`
--

DROP TABLE IF EXISTS `employee_advances`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `employee_advances` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `employeeId` int(11) NOT NULL,
  `date` date NOT NULL,
  `amount` decimal(12,2) NOT NULL,
  `paymentMode` enum('CASH','UPI') NOT NULL,
  `notes` varchar(255) DEFAULT NULL,
  `status` enum('ACTIVE','CANCELLED') NOT NULL DEFAULT 'ACTIVE',
  `createdBy` int(11) DEFAULT NULL,
  `createdAt` datetime(3) NOT NULL DEFAULT current_timestamp(3),
  PRIMARY KEY (`id`),
  KEY `employee_advances_employeeId_date_idx` (`employeeId`,`date`),
  CONSTRAINT `employee_advances_employeeId_fkey` FOREIGN KEY (`employeeId`) REFERENCES `employees` (`id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `employee_advances`
--

LOCK TABLES `employee_advances` WRITE;
/*!40000 ALTER TABLE `employee_advances` DISABLE KEYS */;
/*!40000 ALTER TABLE `employee_advances` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `employee_documents`
--

DROP TABLE IF EXISTS `employee_documents`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `employee_documents` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `employeeId` int(11) NOT NULL,
  `kind` enum('PHOTO','AADHAAR','PAN','OTHER') NOT NULL,
  `mimeType` varchar(40) NOT NULL,
  `size` int(11) NOT NULL,
  `data` mediumblob NOT NULL,
  `createdBy` int(11) DEFAULT NULL,
  `createdAt` datetime(3) NOT NULL DEFAULT current_timestamp(3),
  PRIMARY KEY (`id`),
  KEY `employee_documents_employeeId_kind_idx` (`employeeId`,`kind`),
  CONSTRAINT `employee_documents_employeeId_fkey` FOREIGN KEY (`employeeId`) REFERENCES `employees` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `employee_documents`
--

LOCK TABLES `employee_documents` WRITE;
/*!40000 ALTER TABLE `employee_documents` DISABLE KEYS */;
/*!40000 ALTER TABLE `employee_documents` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `employees`
--

DROP TABLE IF EXISTS `employees`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `employees` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(120) NOT NULL,
  `phone` varchar(15) DEFAULT NULL,
  `designation` varchar(80) DEFAULT NULL,
  `address` varchar(255) DEFAULT NULL,
  `idProofType` varchar(40) DEFAULT NULL,
  `idProofNumber` varchar(40) DEFAULT NULL,
  `joinDate` date DEFAULT NULL,
  `leaveDate` date DEFAULT NULL,
  `monthlySalary` decimal(12,2) NOT NULL,
  `notes` text DEFAULT NULL,
  `active` tinyint(1) NOT NULL DEFAULT 1,
  `createdAt` datetime(3) NOT NULL DEFAULT current_timestamp(3),
  `updatedAt` datetime(3) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `employees`
--

LOCK TABLES `employees` WRITE;
/*!40000 ALTER TABLE `employees` DISABLE KEYS */;
INSERT INTO `employees` VALUES (1,'Dinesh',NULL,'cook',NULL,NULL,NULL,'2026-10-17',NULL,12000.00,NULL,1,'2026-11-18 13:49:52.452','2026-11-18 13:49:52.452'),(2,'Hari Kishun',NULL,'Cook',NULL,NULL,NULL,'2026-10-23',NULL,9000.00,NULL,1,'2026-11-18 13:51:18.737','2026-11-18 13:51:18.737');
/*!40000 ALTER TABLE `employees` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `expense_categories`
--

DROP TABLE IF EXISTS `expense_categories`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `expense_categories` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(80) NOT NULL,
  `nameHi` varchar(80) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `expense_categories_name_key` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `expense_categories`
--

LOCK TABLES `expense_categories` WRITE;
/*!40000 ALTER TABLE `expense_categories` DISABLE KEYS */;
INSERT INTO `expense_categories` VALUES (1,'Electricity','बिजली'),(2,'Wi-Fi / Internet','वाई-फ़ाई / इंटरनेट'),(3,'Rent','किराया'),(4,'Newspaper','अख़बार'),(5,'Water','पानी'),(6,'Gas Cylinder','गैस सिलेंडर'),(7,'Repairs & Maintenance','मरम्मत'),(8,'Transport','ढुलाई / किराया-भाड़ा'),(9,'Staff Food','स्टाफ़ खाना'),(10,'Mobile Recharge','मोबाइल रिचार्ज'),(11,'Licence & Fees','लाइसेंस और फ़ीस'),(12,'Miscellaneous','अन्य');
/*!40000 ALTER TABLE `expense_categories` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `expenses`
--

DROP TABLE IF EXISTS `expenses`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `expenses` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `date` date NOT NULL,
  `categoryId` int(11) NOT NULL,
  `amount` decimal(12,2) NOT NULL,
  `paymentMode` enum('CASH','UPI') NOT NULL,
  `vendorId` int(11) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  `recurringBillId` int(11) DEFAULT NULL,
  `period` varchar(10) DEFAULT NULL,
  `status` enum('ACTIVE','CANCELLED') NOT NULL DEFAULT 'ACTIVE',
  `createdBy` int(11) DEFAULT NULL,
  `createdAt` datetime(3) NOT NULL DEFAULT current_timestamp(3),
  `updatedAt` datetime(3) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `expenses_date_idx` (`date`),
  KEY `expenses_categoryId_date_idx` (`categoryId`,`date`),
  KEY `expenses_recurringBillId_period_idx` (`recurringBillId`,`period`),
  KEY `expenses_vendorId_fkey` (`vendorId`),
  CONSTRAINT `expenses_categoryId_fkey` FOREIGN KEY (`categoryId`) REFERENCES `expense_categories` (`id`) ON UPDATE CASCADE,
  CONSTRAINT `expenses_recurringBillId_fkey` FOREIGN KEY (`recurringBillId`) REFERENCES `recurring_bills` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `expenses_vendorId_fkey` FOREIGN KEY (`vendorId`) REFERENCES `vendors` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `expenses`
--

LOCK TABLES `expenses` WRITE;
/*!40000 ALTER TABLE `expenses` DISABLE KEYS */;
/*!40000 ALTER TABLE `expenses` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `idempotency_keys`
--

DROP TABLE IF EXISTS `idempotency_keys`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `idempotency_keys` (
  `key` varchar(64) NOT NULL,
  `userId` int(11) NOT NULL,
  `method` varchar(10) NOT NULL,
  `path` varchar(255) NOT NULL,
  `statusCode` int(11) NOT NULL,
  `body` mediumtext DEFAULT NULL,
  `createdAt` datetime(3) NOT NULL DEFAULT current_timestamp(3),
  PRIMARY KEY (`key`),
  KEY `idempotency_keys_createdAt_idx` (`createdAt`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `idempotency_keys`
--

LOCK TABLES `idempotency_keys` WRITE;
/*!40000 ALTER TABLE `idempotency_keys` DISABLE KEYS */;
INSERT INTO `idempotency_keys` VALUES ('08d522465d9eabf3f01b15746f16fd34',1,'PATCH','/api/daily-supplies/1',200,'{\"id\":1,\"vendorId\":3,\"itemId\":35,\"defaultQty\":\"3\",\"rate\":\"60\",\"startDate\":\"2026-11-01T00:00:00.000Z\",\"active\":true,\"notes\":null,\"createdAt\":\"2026-11-19T02:12:39.211Z\",\"updatedAt\":\"2026-11-19T15:49:21.344Z\",\"vendor\":{\"id\":3,\"name\":\"Sunny Bhaiya\",\"phone\":null},\"item\":{\"id\":35,\"name\":\"Milk\",\"nameHi\":\"दूध\",\"unit\":\"L\"}}','2026-11-19 15:49:21.338'),('12ab9a0e2408745c2ccc5edea8b6350a',1,'POST','/api/menu-items',201,'{\"id\":11,\"name\":\"Sav mixture 100\",\"nameHi\":null,\"categoryId\":6,\"price\":\"25\",\"active\":true,\"createdAt\":\"2026-11-19T14:42:40.502Z\",\"updatedAt\":\"2026-11-19T14:42:40.502Z\"}','2026-11-19 14:42:40.500'),('16213c3180894c373619b67634fe3e9f',1,'POST','/api/menu-items',201,'{\"id\":21,\"name\":\"Paneer +Roti\",\"nameHi\":null,\"categoryId\":2,\"price\":\"120\",\"active\":true,\"createdAt\":\"2026-11-19T15:09:42.398Z\",\"updatedAt\":\"2026-11-19T15:09:42.398Z\"}','2026-11-19 15:09:42.397'),('1c6a683359abcb6d22bbfef0d4ae492c',1,'POST','/api/menu-items',201,'{\"id\":14,\"name\":\"seasonal Vegetable plate\",\"nameHi\":null,\"categoryId\":2,\"price\":\"30\",\"active\":true,\"createdAt\":\"2026-11-19T15:00:14.433Z\",\"updatedAt\":\"2026-11-19T15:00:14.433Z\"}','2026-11-19 15:00:14.432'),('1cf7638f2f78799aad9e87ec99bc613a',1,'POST','/api/daily-supplies',201,'{\"id\":2,\"vendorId\":4,\"itemId\":61,\"defaultQty\":\"1\",\"rate\":\"4\",\"startDate\":\"2026-11-19T00:00:00.000Z\",\"active\":true,\"notes\":null,\"createdAt\":\"2026-11-19T02:16:44.168Z\",\"updatedAt\":\"2026-11-19T02:16:44.168Z\",\"vendor\":{\"id\":4,\"name\":\"newspaper\",\"phone\":null},\"item\":{\"id\":61,\"name\":\"Newspaper\",\"nameHi\":null,\"unit\":\"pcs\"}}','2026-11-19 02:16:44.167'),('1e3b3e068cdba56b00b8dcccb153cd7f',1,'POST','/api/bills',201,'{\"id\":2,\"date\":\"2026-11-19\",\"tableNo\":null,\"customerId\":null,\"subtotal\":\"110\",\"discount\":\"0\",\"total\":\"110\",\"cashAmount\":\"0\",\"upiAmount\":\"110\",\"notes\":null,\"status\":\"ACTIVE\",\"cancelReason\":null,\"createdBy\":1,\"createdAt\":\"2026-11-19T14:47:33.154Z\",\"updatedAt\":\"2026-11-19T14:47:33.154Z\",\"customer\":null,\"lines\":[{\"id\":3,\"billId\":2,\"menuItemId\":1,\"name\":\"Veg Thali\",\"quantity\":\"1\",\"rate\":\"70\",\"amount\":\"70\"},{\"id\":4,\"billId\":2,\"menuItemId\":7,\"name\":\"Water 1L\",\"quantity\":\"1\",\"rate\":\"20\",\"amount\":\"20\"},{\"id\":5,\"billId\":2,\"menuItemId\":6,\"name\":\"Watter 0.5L\",\"quantity\":\"2\",\"rate\":\"10\",\"amount\":\"20\"}]}','2026-11-19 14:47:33.150'),('203c731d28e01b515a6db62cbb0af608',1,'POST','/api/vendors',201,'{\"id\":5,\"name\":\"Basu chicken shop\",\"phone\":null,\"address\":null,\"notes\":null,\"openingBalance\":\"0\",\"active\":true,\"createdAt\":\"2026-11-19T11:54:02.348Z\",\"updatedAt\":\"2026-11-19T11:54:02.348Z\"}','2026-11-19 11:54:02.346'),('2d3028d82e6a4a88b92f0f517b35bc3f',1,'POST','/api/menu-items',201,'{\"id\":23,\"name\":\"Fish thali\",\"nameHi\":null,\"categoryId\":5,\"price\":\"120\",\"active\":true,\"createdAt\":\"2026-11-19T15:13:18.151Z\",\"updatedAt\":\"2026-11-19T15:13:18.151Z\"}','2026-11-19 15:13:18.149'),('3404424d04b62d44440b8b77d326406e',1,'POST','/api/purchases',201,'{\"id\":6,\"vendorId\":5,\"date\":\"2026-11-19\",\"billNo\":null,\"totalAmount\":\"180\",\"paidAmount\":\"180\",\"paymentMode\":\"CASH\",\"notes\":null,\"status\":\"ACTIVE\",\"createdBy\":1,\"createdAt\":\"2026-11-19T14:34:12.972Z\",\"updatedAt\":\"2026-11-19T14:34:12.972Z\",\"vendor\":{\"id\":5,\"name\":\"Basu chicken shop\"},\"lines\":[{\"id\":7,\"purchaseId\":6,\"itemId\":62,\"quantity\":\"1.25\",\"rate\":\"144\",\"amount\":\"180\",\"item\":{\"id\":62,\"name\":\"Chicken\",\"nameHi\":null,\"unit\":\"kg\"}}],\"_count\":{\"images\":0},\"dueAmount\":\"0\"}','2026-11-19 14:34:12.968'),('3794adfd7ca12442249b5d8588055d7f',1,'POST','/api/attendance',200,'{\"employeeId\":2,\"date\":\"2026-11-17\",\"status\":\"ABSENT\",\"note\":null}','2026-11-18 17:39:20.132'),('38ecf0e96bba0b82798bb7da8e3769dc',1,'POST','/api/items',201,'{\"id\":63,\"name\":\"Green Vegetables\",\"nameHi\":null,\"categoryId\":2,\"unit\":\"kg\",\"currentStock\":\"0\",\"minStock\":\"0\",\"trackStock\":true,\"active\":true,\"createdAt\":\"2026-11-19T13:24:23.507Z\",\"updatedAt\":\"2026-11-19T13:24:23.507Z\"}','2026-11-19 13:24:23.505'),('43232873d979b400dde6a202b3f7b5fe',1,'POST','/api/bills',201,'{\"id\":3,\"date\":\"2026-11-19\",\"tableNo\":null,\"customerId\":null,\"subtotal\":\"290\",\"discount\":\"0\",\"total\":\"290\",\"cashAmount\":\"0\",\"upiAmount\":\"290\",\"notes\":null,\"status\":\"ACTIVE\",\"cancelReason\":null,\"createdBy\":1,\"createdAt\":\"2026-11-19T15:08:36.403Z\",\"updatedAt\":\"2026-11-19T15:08:36.403Z\",\"customer\":null,\"lines\":[{\"id\":6,\"billId\":3,\"menuItemId\":20,\"name\":\"Tadka +Roti\",\"quantity\":\"3\",\"rate\":\"80\",\"amount\":\"240\"},{\"id\":7,\"billId\":3,\"menuItemId\":14,\"name\":\"seasonal Vegetable plate\",\"quantity\":\"1\",\"rate\":\"30\",\"amount\":\"30\"},{\"id\":8,\"billId\":3,\"menuItemId\":7,\"name\":\"Water 1L\",\"quantity\":\"1\",\"rate\":\"20\",\"amount\":\"20\"}]}','2026-11-19 15:08:36.401'),('4532589d0759df1a77912855af5c953e',1,'POST','/api/menu-items',201,'{\"id\":16,\"name\":\"Egg curry\",\"nameHi\":null,\"categoryId\":2,\"price\":\"80\",\"active\":true,\"createdAt\":\"2026-11-19T15:04:15.220Z\",\"updatedAt\":\"2026-11-19T15:04:15.220Z\"}','2026-11-19 15:04:15.219'),('4569c719402e41241b12e9f9427ec826',1,'POST','/api/menu-items',201,'{\"id\":15,\"name\":\"Tadka\",\"nameHi\":null,\"categoryId\":2,\"price\":\"60\",\"active\":true,\"createdAt\":\"2026-11-19T15:00:50.488Z\",\"updatedAt\":\"2026-11-19T15:00:50.488Z\"}','2026-11-19 15:00:50.487'),('46ad0272fc3e013e967d42ffb9d598d4',1,'POST','/api/vendors',201,'{\"id\":4,\"name\":\"newspaper\",\"phone\":null,\"address\":null,\"notes\":null,\"openingBalance\":\"0\",\"active\":true,\"createdAt\":\"2026-11-19T02:14:26.117Z\",\"updatedAt\":\"2026-11-19T02:14:26.117Z\"}','2026-11-19 02:14:26.116'),('470d42fef46b01cb11f3fce2d7e06411',1,'POST','/api/attendance',200,'{\"employeeId\":1,\"date\":\"2026-11-17\",\"status\":\"ABSENT\",\"note\":null}','2026-11-18 17:39:28.849'),('47dc056f0f157f7d55cb02d57c007867',1,'POST','/api/menu-items',201,'{\"id\":19,\"name\":\"Egg Omlet 1 egg\",\"nameHi\":null,\"categoryId\":6,\"price\":\"15\",\"active\":true,\"createdAt\":\"2026-11-19T15:05:56.184Z\",\"updatedAt\":\"2026-11-19T15:05:56.184Z\"}','2026-11-19 15:05:56.183'),('52530478bcc06be7a81a1c0c2210f384',1,'POST','/api/bills',201,'{\"id\":4,\"date\":\"2026-11-19\",\"tableNo\":null,\"customerId\":null,\"subtotal\":\"150\",\"discount\":\"0\",\"total\":\"150\",\"cashAmount\":\"0\",\"upiAmount\":\"150\",\"notes\":null,\"status\":\"ACTIVE\",\"cancelReason\":null,\"createdBy\":1,\"createdAt\":\"2026-11-19T15:10:51.168Z\",\"updatedAt\":\"2026-11-19T15:10:51.168Z\",\"customer\":null,\"lines\":[{\"id\":9,\"billId\":4,\"menuItemId\":21,\"name\":\"Paneer +Roti\",\"quantity\":\"1\",\"rate\":\"120\",\"amount\":\"120\"},{\"id\":10,\"billId\":4,\"menuItemId\":18,\"name\":\"Egg Burji (2 egg)\",\"quantity\":\"1\",\"rate\":\"30\",\"amount\":\"30\"}]}','2026-11-19 15:10:51.163'),('5716dba8cf0d65f5721de60ec2a7a8f2',1,'POST','/api/items',201,'{\"id\":61,\"name\":\"Newspaper\",\"nameHi\":null,\"categoryId\":8,\"unit\":\"pcs\",\"currentStock\":\"0\",\"minStock\":\"0\",\"trackStock\":false,\"active\":true,\"createdAt\":\"2026-11-19T02:15:06.754Z\",\"updatedAt\":\"2026-11-19T02:15:06.754Z\"}','2026-11-19 02:15:06.750'),('61fe4b59509a3fcddd8013077af69307',1,'POST','/api/attendance',200,'{\"employeeId\":1,\"date\":\"2026-11-16\",\"status\":\"ABSENT\",\"note\":null}','2026-11-18 17:39:27.508'),('63725dbe4ac7c815a42e08d021398c26',1,'POST','/api/daily-supplies/1/entries',200,'{\"date\":\"2026-11-18\",\"quantity\":\"2\",\"note\":null}','2026-11-19 15:49:44.891'),('6a28f18dd9fba730c063834f93af2714',1,'POST','/api/menu-items',201,'{\"id\":22,\"name\":\"chicken curry 2 piece\",\"nameHi\":null,\"categoryId\":2,\"price\":\"80\",\"active\":true,\"createdAt\":\"2026-11-19T15:12:39.696Z\",\"updatedAt\":\"2026-11-19T15:12:39.696Z\"}','2026-11-19 15:12:39.694'),('79e28a15e8dd011094e7fa99818b485b',1,'POST','/api/menu-items',201,'{\"id\":17,\"name\":\"Egg curry + Roti\",\"nameHi\":null,\"categoryId\":2,\"price\":\"100\",\"active\":true,\"createdAt\":\"2026-11-19T15:04:35.920Z\",\"updatedAt\":\"2026-11-19T15:04:35.920Z\"}','2026-11-19 15:04:35.896'),('7ae3cf8f34eee7e6b0c4dbc9da2b0b52',1,'POST','/api/vendors',201,'{\"id\":3,\"name\":\"Sunny Bhaiya\",\"phone\":null,\"address\":null,\"notes\":null,\"openingBalance\":\"0\",\"active\":true,\"createdAt\":\"2026-11-19T02:11:31.197Z\",\"updatedAt\":\"2026-11-19T02:11:31.197Z\"}','2026-11-19 02:11:31.196'),('8aaac634b913eb9d4bca16a65b8cd1d4',1,'POST','/api/menu-items',201,'{\"id\":13,\"name\":\"Tea\",\"nameHi\":null,\"categoryId\":7,\"price\":\"10\",\"active\":true,\"createdAt\":\"2026-11-19T14:44:31.935Z\",\"updatedAt\":\"2026-11-19T14:44:31.935Z\"}','2026-11-19 14:44:31.934'),('93cbfb7255d52ceb5af55fb8e7d3c68b',1,'POST','/api/attendance',200,'{\"employeeId\":2,\"date\":\"2026-11-16\",\"status\":\"ABSENT\",\"note\":null}','2026-11-18 17:39:24.540'),('9ce2ea5030bdf09538177035ebc3ac5c',1,'POST','/api/daily-supplies',201,'{\"id\":1,\"vendorId\":3,\"itemId\":35,\"defaultQty\":\"3\",\"rate\":\"60\",\"startDate\":\"2026-11-19T00:00:00.000Z\",\"active\":true,\"notes\":null,\"createdAt\":\"2026-11-19T02:12:39.211Z\",\"updatedAt\":\"2026-11-19T02:12:39.211Z\",\"vendor\":{\"id\":3,\"name\":\"Sunny Bhaiya\",\"phone\":null},\"item\":{\"id\":35,\"name\":\"Milk\",\"nameHi\":\"दूध\",\"unit\":\"L\"}}','2026-11-19 02:12:39.210'),('9f70030019cb754be0f8b945416576b5',1,'POST','/api/vendors',201,'{\"id\":8,\"name\":\"chandbadan Aalo Pyaz\",\"phone\":null,\"address\":null,\"notes\":null,\"openingBalance\":\"0\",\"active\":true,\"createdAt\":\"2026-11-19T13:28:45.342Z\",\"updatedAt\":\"2026-11-19T13:28:45.342Z\"}','2026-11-19 13:28:45.341'),('a07f362870b44407c74fce9b7536992b',1,'PATCH','/api/daily-supplies/2',200,'{\"id\":2,\"vendorId\":4,\"itemId\":61,\"defaultQty\":\"1\",\"rate\":\"4\",\"startDate\":\"2026-11-01T00:00:00.000Z\",\"active\":true,\"notes\":null,\"createdAt\":\"2026-11-19T02:16:44.168Z\",\"updatedAt\":\"2026-11-19T15:51:03.937Z\",\"vendor\":{\"id\":4,\"name\":\"newspaper\",\"phone\":null},\"item\":{\"id\":61,\"name\":\"Newspaper\",\"nameHi\":null,\"unit\":\"pcs\"}}','2026-11-19 15:51:03.935'),('a9d3daa60fae14477929016aa2664d77',1,'POST','/api/purchases',201,'{\"id\":5,\"vendorId\":9,\"date\":\"2026-11-19\",\"billNo\":null,\"totalAmount\":\"150\",\"paidAmount\":\"150\",\"paymentMode\":\"CASH\",\"notes\":null,\"status\":\"ACTIVE\",\"createdBy\":1,\"createdAt\":\"2026-11-19T13:31:00.346Z\",\"updatedAt\":\"2026-11-19T13:31:00.346Z\",\"vendor\":{\"id\":9,\"name\":\"Flipkart\"},\"lines\":[{\"id\":6,\"purchaseId\":5,\"itemId\":2,\"quantity\":\"0.5\",\"rate\":\"300\",\"amount\":\"150\",\"item\":{\"id\":2,\"name\":\"Jeera\",\"nameHi\":\"जीरा\",\"unit\":\"kg\"}}],\"_count\":{\"images\":0},\"dueAmount\":\"0\"}','2026-11-19 13:31:00.343'),('b9c0f4324538c5e694160d2d4f44e412',1,'PATCH','/api/items/61',200,'{\"id\":61,\"name\":\"Newspaper\",\"nameHi\":null,\"categoryId\":null,\"unit\":\"pcs\",\"currentStock\":\"0\",\"minStock\":\"0\",\"trackStock\":false,\"active\":true,\"createdAt\":\"2026-11-19T02:15:06.754Z\",\"updatedAt\":\"2026-11-19T02:15:38.917Z\"}','2026-11-19 02:15:38.915'),('bdf022e3e6f54199518b0ad1e0498cb6',1,'POST','/api/items',201,'{\"id\":62,\"name\":\"Chicken\",\"nameHi\":null,\"categoryId\":7,\"unit\":\"kg\",\"currentStock\":\"0\",\"minStock\":\"0\",\"trackStock\":false,\"active\":true,\"createdAt\":\"2026-11-19T11:54:27.625Z\",\"updatedAt\":\"2026-11-19T11:54:27.625Z\"}','2026-11-19 11:54:27.622'),('ce62d2aa3bd820c6425623ddea4b8d23',1,'POST','/api/bills',201,'{\"id\":1,\"date\":\"2026-11-19\",\"tableNo\":null,\"customerId\":null,\"subtotal\":\"205\",\"discount\":\"0\",\"total\":\"205\",\"cashAmount\":\"205\",\"upiAmount\":\"0\",\"notes\":null,\"status\":\"ACTIVE\",\"cancelReason\":null,\"createdBy\":1,\"createdAt\":\"2026-11-19T14:46:27.324Z\",\"updatedAt\":\"2026-11-19T14:46:27.324Z\",\"customer\":null,\"lines\":[{\"id\":1,\"billId\":1,\"menuItemId\":11,\"name\":\"Sav mixture 100\",\"quantity\":\"3\",\"rate\":\"25\",\"amount\":\"75\"},{\"id\":2,\"billId\":1,\"menuItemId\":13,\"name\":\"Tea\",\"quantity\":\"13\",\"rate\":\"10\",\"amount\":\"130\"}]}','2026-11-19 14:46:27.320'),('d0da41e6722cfbb051556cc644901f6f',1,'POST','/api/menu-items',201,'{\"id\":18,\"name\":\"Egg Burji (2 egg)\",\"nameHi\":null,\"categoryId\":2,\"price\":\"30\",\"active\":true,\"createdAt\":\"2026-11-19T15:05:20.702Z\",\"updatedAt\":\"2026-11-19T15:05:20.702Z\"}','2026-11-19 15:05:20.701'),('d1d8f86d2e3c459dc72d09d87bbe222c',1,'POST','/api/vendors',201,'{\"id\":9,\"name\":\"Flipkart\",\"phone\":null,\"address\":null,\"notes\":null,\"openingBalance\":\"0\",\"active\":true,\"createdAt\":\"2026-11-19T13:30:27.311Z\",\"updatedAt\":\"2026-11-19T13:30:27.311Z\"}','2026-11-19 13:30:27.309'),('d4de6c86031883a4d3396f60f6cdc97f',1,'POST','/api/menu-categories',201,'{\"id\":9,\"name\":\"Other\",\"nameHi\":null,\"sortOrder\":0}','2026-11-19 02:15:23.622'),('db93cc5e55a2618e593eb8c0497b8552',1,'POST','/api/menu-items',201,'{\"id\":12,\"name\":\"sav mixture 50g\",\"nameHi\":null,\"categoryId\":6,\"price\":\"12.5\",\"active\":true,\"createdAt\":\"2026-11-19T14:43:54.600Z\",\"updatedAt\":\"2026-11-19T14:43:54.600Z\"}','2026-11-19 14:43:54.599'),('ddb1ce3e475d1be395b8ec0264d3dbf9',1,'POST','/api/items',201,'{\"id\":64,\"name\":\"Egg\",\"nameHi\":null,\"categoryId\":7,\"unit\":\"dozen\",\"currentStock\":\"0\",\"minStock\":\"0\",\"trackStock\":false,\"active\":true,\"createdAt\":\"2026-11-19T13:25:24.392Z\",\"updatedAt\":\"2026-11-19T13:25:24.392Z\"}','2026-11-19 13:25:24.390'),('de52ebdedd66897dd6e6f3bc69a1a4e1',1,'POST','/api/vendors',201,'{\"id\":7,\"name\":\"vegitable vendor\",\"phone\":null,\"address\":null,\"notes\":null,\"openingBalance\":\"0\",\"active\":true,\"createdAt\":\"2026-11-19T13:23:50.704Z\",\"updatedAt\":\"2026-11-19T13:23:50.704Z\"}','2026-11-19 13:23:50.703'),('e4a875295d6fb6a589137bcdb099fdf1',1,'POST','/api/menu-items',201,'{\"id\":20,\"name\":\"Tadka +Roti\",\"nameHi\":null,\"categoryId\":2,\"price\":\"80\",\"active\":true,\"createdAt\":\"2026-11-19T15:07:06.919Z\",\"updatedAt\":\"2026-11-19T15:07:06.919Z\"}','2026-11-19 15:07:06.918'),('ea42daf3993a1681932d354ad1084be0',1,'POST','/api/vendors',201,'{\"id\":6,\"name\":\"egg vendor arwal mor\",\"phone\":null,\"address\":null,\"notes\":null,\"openingBalance\":\"0\",\"active\":true,\"createdAt\":\"2026-11-19T13:23:37.708Z\",\"updatedAt\":\"2026-11-19T13:23:37.708Z\"}','2026-11-19 13:23:37.703'),('ec73568c3ed6698d5ff54c607c87d3fa',1,'POST','/api/menu-items',201,'{\"id\":24,\"name\":\"Fish curry 2 piece\",\"nameHi\":null,\"categoryId\":2,\"price\":\"80\",\"active\":true,\"createdAt\":\"2026-11-19T15:13:43.829Z\",\"updatedAt\":\"2026-11-19T15:13:43.829Z\"}','2026-11-19 15:13:43.828'),('ed25ccc87bcbb4e88b9b82691c87ed2e',1,'POST','/api/purchases',201,'{\"id\":4,\"vendorId\":8,\"date\":\"2026-11-19\",\"billNo\":null,\"totalAmount\":\"2730\",\"paidAmount\":\"2730\",\"paymentMode\":\"CASH\",\"notes\":null,\"status\":\"ACTIVE\",\"createdBy\":1,\"createdAt\":\"2026-11-19T13:30:00.914Z\",\"updatedAt\":\"2026-11-19T13:30:00.914Z\",\"vendor\":{\"id\":8,\"name\":\"chandbadan Aalo Pyaz\"},\"lines\":[{\"id\":4,\"purchaseId\":4,\"itemId\":37,\"quantity\":\"50\",\"rate\":\"9.6\",\"amount\":\"480\",\"item\":{\"id\":37,\"name\":\"Aloo\",\"nameHi\":\"आलू\",\"unit\":\"kg\"}},{\"id\":5,\"purchaseId\":4,\"itemId\":36,\"quantity\":\"45\",\"rate\":\"50\",\"amount\":\"2250\",\"item\":{\"id\":36,\"name\":\"Pyaz\",\"nameHi\":\"प्याज़\",\"unit\":\"kg\"}}],\"_count\":{\"images\":0},\"dueAmount\":\"0\"}','2026-11-19 13:30:00.910'),('f660cfc684061adb7d5d1a0c789e86db',1,'POST','/api/purchases',201,'{\"id\":2,\"vendorId\":6,\"date\":\"2026-11-19\",\"billNo\":null,\"totalAmount\":\"440\",\"paidAmount\":\"440\",\"paymentMode\":\"CASH\",\"notes\":null,\"status\":\"ACTIVE\",\"createdBy\":1,\"createdAt\":\"2026-11-19T13:26:36.859Z\",\"updatedAt\":\"2026-11-19T13:26:36.859Z\",\"vendor\":{\"id\":6,\"name\":\"egg vendor arwal mor\"},\"lines\":[{\"id\":2,\"purchaseId\":2,\"itemId\":64,\"quantity\":\"60\",\"rate\":\"7.33\",\"amount\":\"440\",\"item\":{\"id\":64,\"name\":\"Egg\",\"nameHi\":null,\"unit\":\"pcs\"}}],\"_count\":{\"images\":0},\"dueAmount\":\"0\"}','2026-11-19 13:26:36.854'),('f980ff8952e021c3dc20f8aefd5c3213',1,'PATCH','/api/items/64',200,'{\"id\":64,\"name\":\"Egg\",\"nameHi\":null,\"categoryId\":7,\"unit\":\"pcs\",\"currentStock\":\"0\",\"minStock\":\"0\",\"trackStock\":false,\"active\":true,\"createdAt\":\"2026-11-19T13:25:24.392Z\",\"updatedAt\":\"2026-11-19T13:25:41.529Z\"}','2026-11-19 13:25:41.527'),('fb3bf4fe8214b504a702ccce39f5edff',1,'POST','/api/daily-supplies/1/entries',200,'{\"date\":\"2026-11-17\",\"quantity\":\"2\",\"note\":null}','2026-11-19 15:49:49.839'),('ffa85bc85f19e3b1a7a44a515d212282',1,'POST','/api/purchases',201,'{\"id\":3,\"vendorId\":7,\"date\":\"2026-11-19\",\"billNo\":null,\"totalAmount\":\"250\",\"paidAmount\":\"250\",\"paymentMode\":\"CASH\",\"notes\":null,\"status\":\"ACTIVE\",\"createdBy\":1,\"createdAt\":\"2026-11-19T13:28:07.087Z\",\"updatedAt\":\"2026-11-19T13:28:07.087Z\",\"vendor\":{\"id\":7,\"name\":\"vegitable vendor\"},\"lines\":[{\"id\":3,\"purchaseId\":3,\"itemId\":63,\"quantity\":\"1\",\"rate\":\"250\",\"amount\":\"250\",\"item\":{\"id\":63,\"name\":\"Green Vegetables\",\"nameHi\":null,\"unit\":\"kg\"}}],\"_count\":{\"images\":0},\"dueAmount\":\"0\"}','2026-11-19 13:28:07.084');
/*!40000 ALTER TABLE `idempotency_keys` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `item_categories`
--

DROP TABLE IF EXISTS `item_categories`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `item_categories` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(80) NOT NULL,
  `nameHi` varchar(80) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `item_categories_name_key` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `item_categories`
--

LOCK TABLES `item_categories` WRITE;
/*!40000 ALTER TABLE `item_categories` DISABLE KEYS */;
INSERT INTO `item_categories` VALUES (1,'Dairy','डेयरी'),(2,'Vegetables','सब्ज़ियाँ'),(3,'Fruits','फल'),(4,'Grocery','किराना'),(5,'Spices','मसाले'),(6,'Oil & Ghee','तेल और घी'),(7,'Meat & Eggs','मांस और अंडे'),(8,'Beverages','पेय'),(9,'Gas & Fuel','गैस और ईंधन'),(10,'Packaging','पैकिंग सामान'),(11,'Cleaning','सफ़ाई सामान');
/*!40000 ALTER TABLE `item_categories` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `items`
--

DROP TABLE IF EXISTS `items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `items` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(120) NOT NULL,
  `nameHi` varchar(120) DEFAULT NULL,
  `categoryId` int(11) DEFAULT NULL,
  `unit` varchar(20) NOT NULL,
  `currentStock` decimal(12,3) NOT NULL DEFAULT 0.000,
  `minStock` decimal(12,3) NOT NULL DEFAULT 0.000,
  `trackStock` tinyint(1) NOT NULL DEFAULT 1,
  `active` tinyint(1) NOT NULL DEFAULT 1,
  `createdAt` datetime(3) NOT NULL DEFAULT current_timestamp(3),
  `updatedAt` datetime(3) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `items_name_key` (`name`),
  KEY `items_categoryId_fkey` (`categoryId`),
  CONSTRAINT `items_categoryId_fkey` FOREIGN KEY (`categoryId`) REFERENCES `item_categories` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=65 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `items`
--

LOCK TABLES `items` WRITE;
/*!40000 ALTER TABLE `items` DISABLE KEYS */;
INSERT INTO `items` VALUES (1,'Chawal (7 Star Basmati)','चावल (7 स्टार बासमती)',4,'kg',50.000,5.000,1,1,'2026-11-14 17:37:03.481','2026-11-18 13:48:16.959'),(2,'Jeera','जीरा',5,'kg',0.500,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-19 13:31:00.347'),(3,'Kali Mirch','काली मिर्च',5,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(4,'Sarson','सरसों',5,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(5,'Kali Sarson','काली सरसों',5,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(6,'Lal Mirch Sabut','लाल मिर्च खड़ी',5,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(7,'Lal Mirch Powder','लाल मिर्च पाउडर',5,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(8,'Haldi','हल्दी',5,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(9,'Dhaniya Powder','धनिया पाउडर',5,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(10,'Ajwain','अजवाइन',5,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(11,'Chicken Masala','चिकन मसाला',5,'packet',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(12,'Mutton Masala','मटन मसाला',5,'packet',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(13,'Garam Masala','गरम मसाला',5,'packet',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(14,'Khada Masala','खड़ा मसाला',5,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(15,'Tej Patta','तेज पत्ता',5,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(16,'Elaichi','इलायची',5,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(17,'Namak','नमक',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(18,'Kala Namak','काला नमक',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(19,'Chini','चीनी',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(20,'Mishri','मिश्री',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(21,'Chai Patti','चाय पत्ती',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(22,'Soya Chunks','सोया चंक्स',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(23,'Chawal (India Gate Basmati)','चावल (इंडिया गेट बासमती)',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(24,'Chawal (Safed Sona)','चावल (सफ़ेद सोना)',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(25,'Chawal (Ladli Basmati)','चावल (लाडली बासमती)',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(26,'Chana Dal','चना दाल',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(27,'Urad Dal','उड़द दाल',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(28,'Moong Dal','मूंग दाल',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(29,'Arhar Dal','अरहर दाल',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(30,'Match Box','माचिस',4,'packet',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(31,'Sarson Tel','सरसों तेल',6,'L',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(32,'Refined Oil','रिफ़ाइंड तेल',6,'L',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(33,'Refined Oil (Saffola)','रिफ़ाइंड तेल (सफोला)',6,'L',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(34,'Refined Oil (Fortune)','रिफ़ाइंड तेल (फॉर्च्यून)',6,'L',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(35,'Milk','दूध',1,'L',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(36,'Pyaz','प्याज़',2,'kg',45.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-19 13:30:00.922'),(37,'Aloo','आलू',2,'kg',50.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-19 13:30:00.916'),(38,'Tamatar','टमाटर',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(39,'Hari Mirch','हरी मिर्च',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(40,'Adrak','अदरक',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(41,'Lahsun','लहसुन',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(42,'Hara Dhaniya','हरा धनिया',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(43,'Pudina','पुदीना',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(44,'Nimbu','नींबू',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(45,'Phool Gobhi','फूल गोभी',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(46,'Patta Gobhi','पत्ता गोभी',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(47,'Shimla Mirch','शिमला मिर्च',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(48,'Matar','मटर',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(49,'Gajar','गाजर',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(50,'Kheera','खीरा',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(51,'Mooli','मूली',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(52,'Palak','पालक',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(53,'Methi','मेथी',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(54,'Baingan','बैंगन',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(55,'Bhindi','भिंडी',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(56,'Lauki','लौकी',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(57,'Mushroom','मशरूम',2,'packet',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(58,'Paneer','पनीर',1,'kg',0.000,0.000,1,1,'2026-11-14 18:35:19.641','2026-11-14 18:35:19.641'),(59,'Ghee','घी',6,'kg',0.000,0.000,1,1,'2026-11-14 18:35:20.011','2026-11-14 18:35:20.011'),(60,'Cheese','चीज़',1,'kg',0.000,0.000,1,1,'2026-11-14 18:35:20.248','2026-11-14 18:35:20.248'),(61,'Newspaper',NULL,NULL,'pcs',0.000,0.000,0,1,'2026-11-19 02:15:06.754','2026-11-19 02:15:38.917'),(62,'Chicken',NULL,7,'kg',0.000,0.000,0,1,'2026-11-19 11:54:27.625','2026-11-19 11:54:27.625'),(63,'Green Vegetables',NULL,2,'kg',1.000,0.000,1,1,'2026-11-19 13:24:23.507','2026-11-19 13:28:07.089'),(64,'Egg',NULL,7,'pcs',0.000,0.000,0,1,'2026-11-19 13:25:24.392','2026-11-19 13:25:41.529');
/*!40000 ALTER TABLE `items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `ledger_entries`
--

DROP TABLE IF EXISTS `ledger_entries`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ledger_entries` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `date` date NOT NULL,
  `account` enum('CASH','UPI') NOT NULL,
  `direction` enum('IN','OUT') NOT NULL,
  `amount` decimal(12,2) NOT NULL,
  `type` enum('OPENING_BALANCE','SALE','PURCHASE','VENDOR_PAYMENT','EXPENSE','SALARY','ADVANCE','OWNER_DEPOSIT','OWNER_WITHDRAWAL','TRANSFER','OTHER_INCOME','OTHER_EXPENSE') NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `refType` varchar(30) DEFAULT NULL,
  `refId` int(11) DEFAULT NULL,
  `partyType` varchar(20) DEFAULT NULL,
  `partyId` int(11) DEFAULT NULL,
  `voided` tinyint(1) NOT NULL DEFAULT 0,
  `createdBy` int(11) DEFAULT NULL,
  `createdAt` datetime(3) NOT NULL DEFAULT current_timestamp(3),
  PRIMARY KEY (`id`),
  KEY `ledger_entries_date_idx` (`date`),
  KEY `ledger_entries_account_date_idx` (`account`,`date`),
  KEY `ledger_entries_refType_refId_idx` (`refType`,`refId`),
  KEY `ledger_entries_partyType_partyId_idx` (`partyType`,`partyId`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ledger_entries`
--

LOCK TABLES `ledger_entries` WRITE;
/*!40000 ALTER TABLE `ledger_entries` DISABLE KEYS */;
INSERT INTO `ledger_entries` VALUES (1,'2026-11-18','UPI','OUT',2800.00,'PURCHASE','Purchase from munna','PURCHASE',1,'VENDOR',1,0,1,'2026-11-18 13:48:16.965'),(2,'2026-11-19','CASH','OUT',440.00,'PURCHASE','Purchase from egg vendor arwal mor','PURCHASE',2,'VENDOR',6,0,1,'2026-11-19 13:26:36.862'),(3,'2026-11-19','CASH','OUT',250.00,'PURCHASE','Purchase from vegitable vendor','PURCHASE',3,'VENDOR',7,0,1,'2026-11-19 13:28:07.093'),(4,'2026-11-19','CASH','OUT',2730.00,'PURCHASE','Purchase from chandbadan Aalo Pyaz','PURCHASE',4,'VENDOR',8,0,1,'2026-11-19 13:30:00.927'),(5,'2026-11-19','CASH','OUT',150.00,'PURCHASE','Purchase from Flipkart','PURCHASE',5,'VENDOR',9,0,1,'2026-11-19 13:31:00.351'),(6,'2026-11-19','CASH','OUT',180.00,'PURCHASE','Purchase from Basu chicken shop','PURCHASE',6,'VENDOR',5,0,1,'2026-11-19 14:34:12.975'),(7,'2026-11-19','CASH','IN',205.00,'SALE','Bill #1','BILL',1,NULL,NULL,0,1,'2026-11-19 14:46:27.327'),(8,'2026-11-19','UPI','IN',110.00,'SALE','Bill #2','BILL',2,NULL,NULL,0,1,'2026-11-19 14:47:33.157'),(9,'2026-11-19','UPI','IN',290.00,'SALE','Bill #3','BILL',3,NULL,NULL,0,1,'2026-11-19 15:08:36.405'),(10,'2026-11-19','UPI','IN',150.00,'SALE','Bill #4','BILL',4,NULL,NULL,0,1,'2026-11-19 15:10:51.170');
/*!40000 ALTER TABLE `ledger_entries` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `menu_categories`
--

DROP TABLE IF EXISTS `menu_categories`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `menu_categories` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(80) NOT NULL,
  `nameHi` varchar(80) DEFAULT NULL,
  `sortOrder` int(11) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `menu_categories_name_key` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `menu_categories`
--

LOCK TABLES `menu_categories` WRITE;
/*!40000 ALTER TABLE `menu_categories` DISABLE KEYS */;
INSERT INTO `menu_categories` VALUES (1,'Breakfast','नाश्ता',1),(2,'Main Course','मुख्य भोजन',2),(3,'Breads','रोटी / पराठा',3),(4,'Rice','चावल',4),(5,'Thali','थाली',5),(6,'Snacks','स्नैक्स',6),(7,'Beverages','पेय',7),(8,'Sweets','मिठाई',8),(9,'Other',NULL,0);
/*!40000 ALTER TABLE `menu_categories` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `menu_items`
--

DROP TABLE IF EXISTS `menu_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `menu_items` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(120) NOT NULL,
  `nameHi` varchar(120) DEFAULT NULL,
  `categoryId` int(11) DEFAULT NULL,
  `price` decimal(12,2) NOT NULL,
  `active` tinyint(1) NOT NULL DEFAULT 1,
  `createdAt` datetime(3) NOT NULL DEFAULT current_timestamp(3),
  `updatedAt` datetime(3) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `menu_items_name_key` (`name`),
  KEY `menu_items_categoryId_fkey` (`categoryId`),
  CONSTRAINT `menu_items_categoryId_fkey` FOREIGN KEY (`categoryId`) REFERENCES `menu_categories` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `menu_items`
--

LOCK TABLES `menu_items` WRITE;
/*!40000 ALTER TABLE `menu_items` DISABLE KEYS */;
INSERT INTO `menu_items` VALUES (1,'Veg Thali',NULL,5,70.00,1,'2026-11-14 17:32:40.270','2026-11-14 17:33:12.923'),(2,'Non veg(Chicken)',NULL,5,120.00,1,'2026-11-14 17:33:07.565','2026-11-14 17:33:07.565'),(3,'Non veg (Mutton)',NULL,5,150.00,1,'2026-11-14 17:33:33.461','2026-11-14 17:33:33.461'),(4,'Samosa',NULL,6,12.50,1,'2026-11-14 17:33:47.500','2026-11-14 17:33:47.500'),(5,'Litti',NULL,6,12.50,1,'2026-11-14 17:34:12.801','2026-11-14 17:34:12.801'),(6,'Watter 0.5L',NULL,7,10.00,1,'2026-11-14 17:34:31.391','2026-11-14 17:34:31.391'),(7,'Water 1L',NULL,7,20.00,1,'2026-11-14 17:34:47.932','2026-11-14 17:34:47.932'),(8,'Roti',NULL,3,8.00,1,'2026-11-14 17:34:57.899','2026-11-14 17:34:57.899'),(9,'Paneer Cury (1 plate)',NULL,2,160.00,1,'2026-11-14 17:35:34.398','2026-11-14 17:35:34.398'),(10,'Paneer Cury (1/2 plate)',NULL,2,80.00,1,'2026-11-14 17:35:50.184','2026-11-14 17:35:50.184'),(11,'Sav mixture 100',NULL,6,25.00,1,'2026-11-19 14:42:40.502','2026-11-19 14:42:40.502'),(12,'sav mixture 50g',NULL,6,12.50,1,'2026-11-19 14:43:54.600','2026-11-19 14:43:54.600'),(13,'Tea',NULL,7,10.00,1,'2026-11-19 14:44:31.935','2026-11-19 14:44:31.935'),(14,'seasonal Vegetable plate',NULL,2,30.00,1,'2026-11-19 15:00:14.433','2026-11-19 15:00:14.433'),(15,'Tadka',NULL,2,60.00,1,'2026-11-19 15:00:50.488','2026-11-19 15:00:50.488'),(16,'Egg curry',NULL,2,80.00,1,'2026-11-19 15:04:15.220','2026-11-19 15:04:15.220'),(17,'Egg curry + Roti',NULL,2,100.00,1,'2026-11-19 15:04:35.920','2026-11-19 15:04:35.920'),(18,'Egg Burji (2 egg)',NULL,2,30.00,1,'2026-11-19 15:05:20.702','2026-11-19 15:05:20.702'),(19,'Egg Omlet 1 egg',NULL,6,15.00,1,'2026-11-19 15:05:56.184','2026-11-19 15:05:56.184'),(20,'Tadka +Roti',NULL,2,80.00,1,'2026-11-19 15:07:06.919','2026-11-19 15:07:06.919'),(21,'Paneer +Roti',NULL,2,120.00,1,'2026-11-19 15:09:42.398','2026-11-19 15:09:42.398'),(22,'chicken curry 2 piece',NULL,2,80.00,1,'2026-11-19 15:12:39.696','2026-11-19 15:12:39.696'),(23,'Fish thali',NULL,5,120.00,1,'2026-11-19 15:13:18.151','2026-11-19 15:13:18.151'),(24,'Fish curry 2 piece',NULL,2,80.00,1,'2026-11-19 15:13:43.829','2026-11-19 15:13:43.829');
/*!40000 ALTER TABLE `menu_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `purchase_images`
--

DROP TABLE IF EXISTS `purchase_images`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `purchase_images` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `purchaseId` int(11) NOT NULL,
  `mimeType` varchar(40) NOT NULL,
  `size` int(11) NOT NULL,
  `data` mediumblob NOT NULL,
  `createdBy` int(11) DEFAULT NULL,
  `createdAt` datetime(3) NOT NULL DEFAULT current_timestamp(3),
  PRIMARY KEY (`id`),
  KEY `purchase_images_purchaseId_idx` (`purchaseId`),
  CONSTRAINT `purchase_images_purchaseId_fkey` FOREIGN KEY (`purchaseId`) REFERENCES `purchases` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `purchase_images`
--

LOCK TABLES `purchase_images` WRITE;
/*!40000 ALTER TABLE `purchase_images` DISABLE KEYS */;
/*!40000 ALTER TABLE `purchase_images` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `purchase_items`
--

DROP TABLE IF EXISTS `purchase_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `purchase_items` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `purchaseId` int(11) NOT NULL,
  `itemId` int(11) NOT NULL,
  `quantity` decimal(12,3) NOT NULL,
  `rate` decimal(12,2) NOT NULL,
  `amount` decimal(12,2) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `purchase_items_purchaseId_fkey` (`purchaseId`),
  KEY `purchase_items_itemId_fkey` (`itemId`),
  CONSTRAINT `purchase_items_itemId_fkey` FOREIGN KEY (`itemId`) REFERENCES `items` (`id`) ON UPDATE CASCADE,
  CONSTRAINT `purchase_items_purchaseId_fkey` FOREIGN KEY (`purchaseId`) REFERENCES `purchases` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `purchase_items`
--

LOCK TABLES `purchase_items` WRITE;
/*!40000 ALTER TABLE `purchase_items` DISABLE KEYS */;
INSERT INTO `purchase_items` VALUES (1,1,1,50.000,56.00,2800.00),(2,2,64,60.000,7.33,440.00),(3,3,63,1.000,250.00,250.00),(4,4,37,50.000,9.60,480.00),(5,4,36,45.000,50.00,2250.00),(6,5,2,0.500,300.00,150.00),(7,6,62,1.250,144.00,180.00);
/*!40000 ALTER TABLE `purchase_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `purchases`
--

DROP TABLE IF EXISTS `purchases`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `purchases` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `vendorId` int(11) NOT NULL,
  `date` date NOT NULL,
  `billNo` varchar(50) DEFAULT NULL,
  `totalAmount` decimal(12,2) NOT NULL,
  `paidAmount` decimal(12,2) NOT NULL DEFAULT 0.00,
  `paymentMode` enum('CASH','UPI') DEFAULT NULL,
  `notes` varchar(255) DEFAULT NULL,
  `status` enum('ACTIVE','CANCELLED') NOT NULL DEFAULT 'ACTIVE',
  `createdBy` int(11) DEFAULT NULL,
  `createdAt` datetime(3) NOT NULL DEFAULT current_timestamp(3),
  `updatedAt` datetime(3) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `purchases_date_idx` (`date`),
  KEY `purchases_vendorId_date_idx` (`vendorId`,`date`),
  CONSTRAINT `purchases_vendorId_fkey` FOREIGN KEY (`vendorId`) REFERENCES `vendors` (`id`) ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `purchases`
--

LOCK TABLES `purchases` WRITE;
/*!40000 ALTER TABLE `purchases` DISABLE KEYS */;
INSERT INTO `purchases` VALUES (1,1,'2026-11-18',NULL,2800.00,2800.00,'UPI',NULL,'ACTIVE',1,'2026-11-18 13:48:16.957','2026-11-18 13:48:16.957'),(2,6,'2026-11-19',NULL,440.00,440.00,'CASH',NULL,'ACTIVE',1,'2026-11-19 13:26:36.859','2026-11-19 13:26:36.859'),(3,7,'2026-11-19',NULL,250.00,250.00,'CASH',NULL,'ACTIVE',1,'2026-11-19 13:28:07.087','2026-11-19 13:28:07.087'),(4,8,'2026-11-19',NULL,2730.00,2730.00,'CASH',NULL,'ACTIVE',1,'2026-11-19 13:30:00.914','2026-11-19 13:30:00.914'),(5,9,'2026-11-19',NULL,150.00,150.00,'CASH',NULL,'ACTIVE',1,'2026-11-19 13:31:00.346','2026-11-19 13:31:00.346'),(6,5,'2026-11-19',NULL,180.00,180.00,'CASH',NULL,'ACTIVE',1,'2026-11-19 14:34:12.972','2026-11-19 14:34:12.972');
/*!40000 ALTER TABLE `purchases` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `recurring_bills`
--

DROP TABLE IF EXISTS `recurring_bills`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `recurring_bills` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(120) NOT NULL,
  `nameHi` varchar(120) DEFAULT NULL,
  `categoryId` int(11) NOT NULL,
  `vendorId` int(11) DEFAULT NULL,
  `frequency` enum('DAILY','MONTHLY') NOT NULL DEFAULT 'MONTHLY',
  `defaultAmount` decimal(12,2) DEFAULT NULL,
  `dueDay` int(11) DEFAULT NULL,
  `active` tinyint(1) NOT NULL DEFAULT 1,
  `notes` varchar(255) DEFAULT NULL,
  `createdAt` datetime(3) NOT NULL DEFAULT current_timestamp(3),
  `updatedAt` datetime(3) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `recurring_bills_categoryId_fkey` (`categoryId`),
  KEY `recurring_bills_vendorId_fkey` (`vendorId`),
  CONSTRAINT `recurring_bills_categoryId_fkey` FOREIGN KEY (`categoryId`) REFERENCES `expense_categories` (`id`) ON UPDATE CASCADE,
  CONSTRAINT `recurring_bills_vendorId_fkey` FOREIGN KEY (`vendorId`) REFERENCES `vendors` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recurring_bills`
--

LOCK TABLES `recurring_bills` WRITE;
/*!40000 ALTER TABLE `recurring_bills` DISABLE KEYS */;
/*!40000 ALTER TABLE `recurring_bills` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `salary_payments`
--

DROP TABLE IF EXISTS `salary_payments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `salary_payments` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `employeeId` int(11) NOT NULL,
  `month` varchar(7) NOT NULL,
  `date` date NOT NULL,
  `grossSalary` decimal(12,2) NOT NULL,
  `bonus` decimal(12,2) NOT NULL DEFAULT 0.00,
  `advanceDeduction` decimal(12,2) NOT NULL DEFAULT 0.00,
  `otherDeduction` decimal(12,2) NOT NULL DEFAULT 0.00,
  `netPaid` decimal(12,2) NOT NULL,
  `paymentMode` enum('CASH','UPI') NOT NULL,
  `notes` varchar(255) DEFAULT NULL,
  `status` enum('ACTIVE','CANCELLED') NOT NULL DEFAULT 'ACTIVE',
  `createdBy` int(11) DEFAULT NULL,
  `createdAt` datetime(3) NOT NULL DEFAULT current_timestamp(3),
  PRIMARY KEY (`id`),
  KEY `salary_payments_employeeId_month_idx` (`employeeId`,`month`),
  KEY `salary_payments_month_idx` (`month`),
  CONSTRAINT `salary_payments_employeeId_fkey` FOREIGN KEY (`employeeId`) REFERENCES `employees` (`id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `salary_payments`
--

LOCK TABLES `salary_payments` WRITE;
/*!40000 ALTER TABLE `salary_payments` DISABLE KEYS */;
/*!40000 ALTER TABLE `salary_payments` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_count_items`
--

DROP TABLE IF EXISTS `stock_count_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_count_items` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `stockCountId` int(11) NOT NULL,
  `itemId` int(11) NOT NULL,
  `systemQty` decimal(12,3) NOT NULL,
  `countedQty` decimal(12,3) NOT NULL,
  `difference` decimal(12,3) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_count_items_stockCountId_fkey` (`stockCountId`),
  KEY `stock_count_items_itemId_fkey` (`itemId`),
  CONSTRAINT `stock_count_items_itemId_fkey` FOREIGN KEY (`itemId`) REFERENCES `items` (`id`) ON UPDATE CASCADE,
  CONSTRAINT `stock_count_items_stockCountId_fkey` FOREIGN KEY (`stockCountId`) REFERENCES `stock_counts` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_count_items`
--

LOCK TABLES `stock_count_items` WRITE;
/*!40000 ALTER TABLE `stock_count_items` DISABLE KEYS */;
/*!40000 ALTER TABLE `stock_count_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_counts`
--

DROP TABLE IF EXISTS `stock_counts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_counts` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `date` date NOT NULL,
  `notes` varchar(255) DEFAULT NULL,
  `createdBy` int(11) DEFAULT NULL,
  `createdAt` datetime(3) NOT NULL DEFAULT current_timestamp(3),
  PRIMARY KEY (`id`),
  KEY `stock_counts_date_idx` (`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_counts`
--

LOCK TABLES `stock_counts` WRITE;
/*!40000 ALTER TABLE `stock_counts` DISABLE KEYS */;
/*!40000 ALTER TABLE `stock_counts` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_movements`
--

DROP TABLE IF EXISTS `stock_movements`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_movements` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `itemId` int(11) NOT NULL,
  `type` enum('OPENING','PURCHASE','PURCHASE_CANCEL','USAGE','WASTAGE','COUNT_ADJUSTMENT') NOT NULL,
  `quantity` decimal(12,3) NOT NULL,
  `date` date NOT NULL,
  `refType` varchar(30) DEFAULT NULL,
  `refId` int(11) DEFAULT NULL,
  `note` varchar(255) DEFAULT NULL,
  `createdBy` int(11) DEFAULT NULL,
  `createdAt` datetime(3) NOT NULL DEFAULT current_timestamp(3),
  PRIMARY KEY (`id`),
  KEY `stock_movements_itemId_date_idx` (`itemId`,`date`),
  KEY `stock_movements_refType_refId_idx` (`refType`,`refId`),
  CONSTRAINT `stock_movements_itemId_fkey` FOREIGN KEY (`itemId`) REFERENCES `items` (`id`) ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_movements`
--

LOCK TABLES `stock_movements` WRITE;
/*!40000 ALTER TABLE `stock_movements` DISABLE KEYS */;
INSERT INTO `stock_movements` VALUES (1,1,'PURCHASE',50.000,'2026-11-18','PURCHASE',1,'From munna',1,'2026-11-18 13:48:16.961'),(2,63,'PURCHASE',1.000,'2026-11-19','PURCHASE',3,'From vegitable vendor',1,'2026-11-19 13:28:07.090'),(3,37,'PURCHASE',50.000,'2026-11-19','PURCHASE',4,'From chandbadan Aalo Pyaz',1,'2026-11-19 13:30:00.920'),(4,36,'PURCHASE',45.000,'2026-11-19','PURCHASE',4,'From chandbadan Aalo Pyaz',1,'2026-11-19 13:30:00.924'),(5,2,'PURCHASE',0.500,'2026-11-19','PURCHASE',5,'From Flipkart',1,'2026-11-19 13:31:00.349');
/*!40000 ALTER TABLE `stock_movements` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `username` varchar(50) NOT NULL,
  `phone` varchar(15) DEFAULT NULL,
  `passwordHash` varchar(100) NOT NULL,
  `role` enum('OWNER','MANAGER') NOT NULL DEFAULT 'MANAGER',
  `language` enum('EN','HI') NOT NULL DEFAULT 'EN',
  `active` tinyint(1) NOT NULL DEFAULT 1,
  `createdAt` datetime(3) NOT NULL DEFAULT current_timestamp(3),
  `updatedAt` datetime(3) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `users_username_key` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'Owner','owner',NULL,'$2b$10$aNxGcHpM9ANWZ4zFNJ2G8um.E2nRbg05ljP19fqd4ah/JvaZk23OC','OWNER','EN',1,'2026-11-14 17:07:57.367','2026-11-18 16:36:03.866');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `vendor_item_prices`
--

DROP TABLE IF EXISTS `vendor_item_prices`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `vendor_item_prices` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `vendorId` int(11) NOT NULL,
  `itemId` int(11) NOT NULL,
  `price` decimal(12,2) NOT NULL,
  `effectiveFrom` date NOT NULL,
  `notes` varchar(255) DEFAULT NULL,
  `createdAt` datetime(3) NOT NULL DEFAULT current_timestamp(3),
  PRIMARY KEY (`id`),
  KEY `vendor_item_prices_itemId_effectiveFrom_idx` (`itemId`,`effectiveFrom`),
  KEY `vendor_item_prices_vendorId_itemId_effectiveFrom_idx` (`vendorId`,`itemId`,`effectiveFrom`),
  CONSTRAINT `vendor_item_prices_itemId_fkey` FOREIGN KEY (`itemId`) REFERENCES `items` (`id`) ON UPDATE CASCADE,
  CONSTRAINT `vendor_item_prices_vendorId_fkey` FOREIGN KEY (`vendorId`) REFERENCES `vendors` (`id`) ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `vendor_item_prices`
--

LOCK TABLES `vendor_item_prices` WRITE;
/*!40000 ALTER TABLE `vendor_item_prices` DISABLE KEYS */;
INSERT INTO `vendor_item_prices` VALUES (1,1,1,56.00,'2026-11-18','Purchase #1','2026-11-18 13:48:16.964'),(2,6,64,7.33,'2026-11-19','Purchase #2','2026-11-19 13:26:36.861'),(3,7,63,250.00,'2026-11-19','Purchase #3','2026-11-19 13:28:07.092'),(4,8,37,9.60,'2026-11-19','Purchase #4','2026-11-19 13:30:00.922'),(5,8,36,50.00,'2026-11-19','Purchase #4','2026-11-19 13:30:00.925'),(6,9,2,300.00,'2026-11-19','Purchase #5','2026-11-19 13:31:00.350'),(7,5,62,144.00,'2026-11-19','Purchase #6','2026-11-19 14:34:12.974');
/*!40000 ALTER TABLE `vendor_item_prices` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `vendor_payments`
--

DROP TABLE IF EXISTS `vendor_payments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `vendor_payments` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `vendorId` int(11) NOT NULL,
  `date` date NOT NULL,
  `amount` decimal(12,2) NOT NULL,
  `paymentMode` enum('CASH','UPI') NOT NULL,
  `notes` varchar(255) DEFAULT NULL,
  `status` enum('ACTIVE','CANCELLED') NOT NULL DEFAULT 'ACTIVE',
  `createdBy` int(11) DEFAULT NULL,
  `createdAt` datetime(3) NOT NULL DEFAULT current_timestamp(3),
  PRIMARY KEY (`id`),
  KEY `vendor_payments_vendorId_date_idx` (`vendorId`,`date`),
  CONSTRAINT `vendor_payments_vendorId_fkey` FOREIGN KEY (`vendorId`) REFERENCES `vendors` (`id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `vendor_payments`
--

LOCK TABLES `vendor_payments` WRITE;
/*!40000 ALTER TABLE `vendor_payments` DISABLE KEYS */;
/*!40000 ALTER TABLE `vendor_payments` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `vendors`
--

DROP TABLE IF EXISTS `vendors`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `vendors` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(120) NOT NULL,
  `phone` varchar(15) DEFAULT NULL,
  `address` varchar(255) DEFAULT NULL,
  `notes` text DEFAULT NULL,
  `openingBalance` decimal(12,2) NOT NULL DEFAULT 0.00,
  `active` tinyint(1) NOT NULL DEFAULT 1,
  `createdAt` datetime(3) NOT NULL DEFAULT current_timestamp(3),
  `updatedAt` datetime(3) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `vendors`
--

LOCK TABLES `vendors` WRITE;
/*!40000 ALTER TABLE `vendors` DISABLE KEYS */;
INSERT INTO `vendors` VALUES (1,'munna',NULL,NULL,NULL,0.00,1,'2026-11-18 13:46:12.933','2026-11-18 13:46:12.933'),(2,'Ajay Dharhara',NULL,NULL,NULL,0.00,1,'2026-11-18 13:52:55.128','2026-11-18 13:52:55.128'),(3,'Sunny Bhaiya',NULL,NULL,NULL,0.00,1,'2026-11-19 02:11:31.197','2026-11-19 02:11:31.197'),(4,'newspaper',NULL,NULL,NULL,0.00,1,'2026-11-19 02:14:26.117','2026-11-19 02:14:26.117'),(5,'Basu chicken shop',NULL,NULL,NULL,0.00,1,'2026-11-19 11:54:02.348','2026-11-19 11:54:02.348'),(6,'egg vendor arwal mor',NULL,NULL,NULL,0.00,1,'2026-11-19 13:23:37.708','2026-11-19 13:23:37.708'),(7,'vegitable vendor',NULL,NULL,NULL,0.00,1,'2026-11-19 13:23:50.704','2026-11-19 13:23:50.704'),(8,'chandbadan Aalo Pyaz',NULL,NULL,NULL,0.00,1,'2026-11-19 13:28:45.342','2026-11-19 13:28:45.342'),(9,'Flipkart',NULL,NULL,NULL,0.00,1,'2026-11-19 13:30:27.311','2026-11-19 13:30:27.311');
/*!40000 ALTER TABLE `vendors` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping routines for database 'u662998774_purnima_vatika'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-11-19 17:48:48
