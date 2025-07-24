-- SQLite Database Initialization Script for Influencer Sponsorship System


PRAGMA foreign_keys = ON;



-- Table structure for table `influencer`
CREATE TABLE IF NOT EXISTS influencer (
  influencerid INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  handle TEXT NOT NULL UNIQUE,
  follower_count INTEGER,
  status TEXT CHECK(status IN ('Active', 'Inactive')) NOT NULL
);


INSERT INTO influencer (name, handle, follower_count, status) VALUES
('John Doe', '@johndoe', 150000, 'Active'),
('Jane Smith', '@janesmith', 200000, 'Active');

-- --------------------------------------------------------

-- Table structure for table `sponsorship`
CREATE TABLE IF NOT EXISTS sponsorship (
  sponsorshipid INTEGER PRIMARY KEY AUTOINCREMENT,
  influencerid INTEGER NOT NULL,
  campaignid INTEGER NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  amount REAL NOT NULL,
  status TEXT CHECK(status IN ('Ongoing', 'Completed', 'Cancelled')) NOT NULL,
  FOREIGN KEY (influencerid) REFERENCES influencer(influencerid),
  FOREIGN KEY (campaignid) REFERENCES campaign(campaignid)
);


INSERT INTO sponsorship (influencerid, campaignid, start_date, end_date, amount, status) VALUES
(1, 1, '2024-01-01', '2024-03-31', 5000.00, 'Ongoing'),
(2, 2, '2024-02-01', '2024-04-30', 7000.00, 'Completed');

-- --------------------------------------------------------

-- Table structure for table `campaign`
CREATE TABLE IF NOT EXISTS campaign (
  campaignid INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  budget REAL NOT NULL
);


INSERT INTO campaign (name, start_date, end_date, budget) VALUES
('Spring Collection Launch', '2024-01-01', '2024-03-31', 20000.00),
('Summer Sale Promotion', '2024-02-01', '2024-04-30', 30000.00);

-- --------------------------------------------------------

-- Table structure for table `brand`
CREATE TABLE IF NOT EXISTS brand (
  brandid INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  industry TEXT NOT NULL,
  status TEXT CHECK(status IN ('Active', 'Inactive')) NOT NULL
);


INSERT INTO brand (name, industry, status) VALUES
('Brand A', 'Fashion', 'Active'),
('Brand B', 'Electronics', 'Inactive');

-- --------------------------------------------------------

-- Table structure for table `post`
CREATE TABLE IF NOT EXISTS post (
  postid INTEGER PRIMARY KEY AUTOINCREMENT,
  influencerid INTEGER NOT NULL,
  campaignid INTEGER NOT NULL,
  content TEXT NOT NULL,
  post_date DATE NOT NULL,
  engagement INTEGER,
  FOREIGN KEY (influencerid) REFERENCES influencer(influencerid),
  FOREIGN KEY (campaignid) REFERENCES campaign(campaignid)
);


INSERT INTO post (influencerid, campaignid, content, post_date, engagement) VALUES
(1, 1, 'Excited to partner with Brand A for their Spring Collection!', '2024-01-10', 12000),
(2, 2, 'Check out Brand B’s latest summer sale!', '2024-02-15', 15000);

-- --------------------------------------------------------

-- Table structure for table `brand_campaign`
CREATE TABLE IF NOT EXISTS brand_campaign (
  brand_campaignid INTEGER PRIMARY KEY AUTOINCREMENT,
  brandid INTEGER NOT NULL,
  campaignid INTEGER NOT NULL,
  FOREIGN KEY (brandid) REFERENCES brand(brandid),
  FOREIGN KEY (campaignid) REFERENCES campaign(campaignid)
);


INSERT INTO brand_campaign (brandid, campaignid) VALUES
(1, 1),
(2, 2);

-- --------------------------------------------------------

-- Table structure for table `campaign_influencer`
CREATE TABLE IF NOT EXISTS campaign_influencer (
  campaign_influencerid INTEGER PRIMARY KEY AUTOINCREMENT,
  campaignid INTEGER NOT NULL,
  influencerid INTEGER NOT NULL,
  FOREIGN KEY (campaignid) REFERENCES campaign(campaignid),
  FOREIGN KEY (influencerid) REFERENCES influencer(influencerid)
);


INSERT INTO campaign_influencer (campaignid, influencerid) VALUES
(1, 1),
(2, 2);

-- --------------------------------------------------------

-- Table structure for table `payment`
CREATE TABLE IF NOT EXISTS payment (
  paymentid INTEGER PRIMARY KEY AUTOINCREMENT,
  sponsorshipid INTEGER NOT NULL,
  payment_date DATE NOT NULL,
  amount REAL NOT NULL,
  status TEXT CHECK(status IN ('Paid', 'Pending', 'Cancelled')) NOT NULL,
  FOREIGN KEY (sponsorshipid) REFERENCES sponsorship(sponsorshipid)
);


INSERT INTO payment (sponsorshipid, payment_date, amount, status) VALUES
(1, '2024-01-05', 2500.00, 'Paid'),
(2, '2024-02-10', 3500.00, 'Paid');
