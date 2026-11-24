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
INSERT INTO `_prisma_migrations` VALUES ('3783fb5c-5f93-431c-b4cf-9b4abfc9662c','bd9b85ffcfaf9e22fb18b97981dc516e18d41c65d3b81ee4e81b9c3d03b4f278','2026-11-14 17:07:47.643','20261114052011_init',NULL,NULL,'2026-11-14 17:07:46.978',1);
/*!40000 ALTER TABLE `_prisma_migrations` ENABLE KEYS */;
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `bill_items`
--

LOCK TABLES `bill_items` WRITE;
/*!40000 ALTER TABLE `bill_items` DISABLE KEYS */;
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `bills`
--

LOCK TABLES `bills` WRITE;
/*!40000 ALTER TABLE `bills` DISABLE KEYS */;
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `employees`
--

LOCK TABLES `employees` WRITE;
/*!40000 ALTER TABLE `employees` DISABLE KEYS */;
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
) ENGINE=InnoDB AUTO_INCREMENT=58 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `items`
--

LOCK TABLES `items` WRITE;
/*!40000 ALTER TABLE `items` DISABLE KEYS */;
INSERT INTO `items` VALUES (1,'Chawal (7 Star Basmati)','चावल (7 स्टार बासमती)',4,'kg',0.000,5.000,1,1,'2026-11-14 17:37:03.481','2026-11-14 18:08:04.343'),(2,'Jeera','जीरा',5,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(3,'Kali Mirch','काली मिर्च',5,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(4,'Sarson','सरसों',5,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(5,'Kali Sarson','काली सरसों',5,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(6,'Lal Mirch Sabut','लाल मिर्च खड़ी',5,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(7,'Lal Mirch Powder','लाल मिर्च पाउडर',5,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(8,'Haldi','हल्दी',5,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(9,'Dhaniya Powder','धनिया पाउडर',5,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(10,'Ajwain','अजवाइन',5,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(11,'Chicken Masala','चिकन मसाला',5,'packet',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(12,'Mutton Masala','मटन मसाला',5,'packet',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(13,'Garam Masala','गरम मसाला',5,'packet',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(14,'Khada Masala','खड़ा मसाला',5,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(15,'Tej Patta','तेज पत्ता',5,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(16,'Elaichi','इलायची',5,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(17,'Namak','नमक',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(18,'Kala Namak','काला नमक',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(19,'Chini','चीनी',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(20,'Mishri','मिश्री',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(21,'Chai Patti','चाय पत्ती',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(22,'Soya Chunks','सोया चंक्स',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(23,'Chawal (India Gate Basmati)','चावल (इंडिया गेट बासमती)',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(24,'Chawal (Safed Sona)','चावल (सफ़ेद सोना)',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(25,'Chawal (Ladli Basmati)','चावल (लाडली बासमती)',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(26,'Chana Dal','चना दाल',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(27,'Urad Dal','उड़द दाल',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(28,'Moong Dal','मूंग दाल',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(29,'Arhar Dal','अरहर दाल',4,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(30,'Match Box','माचिस',4,'packet',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(31,'Sarson Tel','सरसों तेल',6,'L',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(32,'Refined Oil','रिफ़ाइंड तेल',6,'L',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(33,'Refined Oil (Saffola)','रिफ़ाइंड तेल (सफोला)',6,'L',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(34,'Refined Oil (Fortune)','रिफ़ाइंड तेल (फॉर्च्यून)',6,'L',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(35,'Milk','दूध',1,'L',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(36,'Pyaz','प्याज़',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(37,'Aloo','आलू',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(38,'Tamatar','टमाटर',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(39,'Hari Mirch','हरी मिर्च',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(40,'Adrak','अदरक',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(41,'Lahsun','लहसुन',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(42,'Hara Dhaniya','हरा धनिया',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(43,'Pudina','पुदीना',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(44,'Nimbu','नींबू',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(45,'Phool Gobhi','फूल गोभी',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(46,'Patta Gobhi','पत्ता गोभी',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(47,'Shimla Mirch','शिमला मिर्च',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(48,'Matar','मटर',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(49,'Gajar','गाजर',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(50,'Kheera','खीरा',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(51,'Mooli','मूली',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(52,'Palak','पालक',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(53,'Methi','मेथी',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(54,'Baingan','बैंगन',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(55,'Bhindi','भिंडी',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(56,'Lauki','लौकी',2,'kg',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652'),(57,'Mushroom','मशरूम',2,'packet',0.000,0.000,1,1,'2026-11-14 18:08:05.652','2026-11-14 18:08:05.652');
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ledger_entries`
--

LOCK TABLES `ledger_entries` WRITE;
/*!40000 ALTER TABLE `ledger_entries` DISABLE KEYS */;
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
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `menu_categories`
--

LOCK TABLES `menu_categories` WRITE;
/*!40000 ALTER TABLE `menu_categories` DISABLE KEYS */;
INSERT INTO `menu_categories` VALUES (1,'Breakfast','नाश्ता',1),(2,'Main Course','मुख्य भोजन',2),(3,'Breads','रोटी / पराठा',3),(4,'Rice','चावल',4),(5,'Thali','थाली',5),(6,'Snacks','स्नैक्स',6),(7,'Beverages','पेय',7),(8,'Sweets','मिठाई',8);
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
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `menu_items`
--

LOCK TABLES `menu_items` WRITE;
/*!40000 ALTER TABLE `menu_items` DISABLE KEYS */;
INSERT INTO `menu_items` VALUES (1,'Veg Thali',NULL,5,70.00,1,'2026-11-14 17:32:40.270','2026-11-14 17:33:12.923'),(2,'Non veg(Chicken)',NULL,5,120.00,1,'2026-11-14 17:33:07.565','2026-11-14 17:33:07.565'),(3,'Non veg (Mutton)',NULL,5,150.00,1,'2026-11-14 17:33:33.461','2026-11-14 17:33:33.461'),(4,'Samosa',NULL,6,12.50,1,'2026-11-14 17:33:47.500','2026-11-14 17:33:47.500'),(5,'Litti',NULL,6,12.50,1,'2026-11-14 17:34:12.801','2026-11-14 17:34:12.801'),(6,'Watter 0.5L',NULL,7,10.00,1,'2026-11-14 17:34:31.391','2026-11-14 17:34:31.391'),(7,'Water 1L',NULL,7,20.00,1,'2026-11-14 17:34:47.932','2026-11-14 17:34:47.932'),(8,'Roti',NULL,3,8.00,1,'2026-11-14 17:34:57.899','2026-11-14 17:34:57.899'),(9,'Paneer Cury (1 plate)',NULL,2,160.00,1,'2026-11-14 17:35:34.398','2026-11-14 17:35:34.398'),(10,'Paneer Cury (1/2 plate)',NULL,2,80.00,1,'2026-11-14 17:35:50.184','2026-11-14 17:35:50.184');
/*!40000 ALTER TABLE `menu_items` ENABLE KEYS */;
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `purchase_items`
--

LOCK TABLES `purchase_items` WRITE;
/*!40000 ALTER TABLE `purchase_items` DISABLE KEYS */;
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `purchases`
--

LOCK TABLES `purchases` WRITE;
/*!40000 ALTER TABLE `purchases` DISABLE KEYS */;
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_movements`
--

LOCK TABLES `stock_movements` WRITE;
/*!40000 ALTER TABLE `stock_movements` DISABLE KEYS */;
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
INSERT INTO `users` VALUES (1,'Owner','owner',NULL,'$2b$10$ALg4vukYIE2m97QoelQAAORevedxw0Hg3U0CVQEpwSsjOQ4xk/mF2','OWNER','EN',1,'2026-11-14 17:07:57.367','2026-11-14 18:32:19.171');
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `vendor_item_prices`
--

LOCK TABLES `vendor_item_prices` WRITE;
/*!40000 ALTER TABLE `vendor_item_prices` DISABLE KEYS */;
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `vendors`
--

LOCK TABLES `vendors` WRITE;
/*!40000 ALTER TABLE `vendors` DISABLE KEYS */;
/*!40000 ALTER TABLE `vendors` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-11-14 18:35:01
