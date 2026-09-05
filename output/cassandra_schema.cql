-- Cassandra Schema Migration Suggestion
-- Generated based on semantic clustering analysis

CREATE KEYSPACE IF NOT EXISTS migrated_db
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 3};

USE migrated_db;

-- Cluster 0: Combines customers
CREATE TABLE IF NOT EXISTS customers_data (
    customers_CREDITCARDTYPE text,
    customers_CREDITCARD text,
    customers_CREDITCARDEXPIRATION text,
    PRIMARY KEY (customers_CREDITCARDTYPE)
);

-- Cluster 1: Combines reorder, orderlines, orders
CREATE TABLE IF NOT EXISTS orderlines_orders_reorder_data (
    orderlines_ORDERDATE text,
    orders_ORDERDATE text,
    reorder_DATE_LOW text,
    reorder_QUAN_LOW text,
    reorder_DATE_REORDERED text,
    reorder_QUAN_REORDERED text,
    reorder_DATE_EXPECTED text,
    PRIMARY KEY (orderlines_ORDERDATE)
);

-- Cluster 2: Combines cust_hist, customers
CREATE TABLE IF NOT EXISTS cust_hist_customers_data (
    cust_hist_CUSTOMERID text,
    customers_CUSTOMERID text,
    customers_FIRSTNAME text,
    customers_LASTNAME text,
    customers_ADDRESS1 text,
    customers_ADDRESS2 text,
    customers_USERNAME text,
    customers_GENDER text,
    PRIMARY KEY (cust_hist_CUSTOMERID)
);

-- Cluster 3: Combines products, categories, inventory
CREATE TABLE IF NOT EXISTS categories_inventory_products_data (
    categories_CATEGORY text,
    categories_CATEGORYNAME text,
    inventory_SALES text,
    products_CATEGORY text,
    products_TITLE text,
    products_ACTOR text,
    products_PRICE text,
    products_SPECIAL text,
    PRIMARY KEY (categories_CATEGORY)
);

-- Cluster 4: Combines customers
CREATE TABLE IF NOT EXISTS customers_data (
    customers_CITY text,
    customers_STATE text,
    customers_ZIP text,
    customers_COUNTRY text,
    customers_REGION text,
    customers_EMAIL text,
    customers_PHONE text,
    customers_PASSWORD text,
    customers_AGE text,
    customers_INCOME text,
    PRIMARY KEY (customers_CITY)
);

-- Cluster 5: Combines cust_hist, orderlines
CREATE TABLE IF NOT EXISTS cust_hist_orderlines_data (
    cust_hist_ORDERID text,
    orderlines_ORDERLINEID text,
    orderlines_ORDERID text,
    orderlines_PROD_ID text,
    orderlines_QUANTITY text,
    PRIMARY KEY (cust_hist_ORDERID)
);

-- Cluster 6: Combines cust_hist, reorder, products, inventory
CREATE TABLE IF NOT EXISTS cust_hist_inventory_products_reorder_data (
    cust_hist_PROD_ID text,
    inventory_PROD_ID text,
    inventory_QUAN_IN_STOCK text,
    products_PROD_ID text,
    products_COMMON_PROD_ID text,
    reorder_PROD_ID text,
    PRIMARY KEY (cust_hist_PROD_ID)
);

-- Cluster 7: Combines orders
CREATE TABLE IF NOT EXISTS orders_data (
    orders_ORDERID text,
    orders_CUSTOMERID text,
    orders_NETAMOUNT text,
    orders_TAX text,
    orders_TOTALAMOUNT text,
    PRIMARY KEY (orders_ORDERID)
);
