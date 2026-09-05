-- mysqlds2_create_sp.sql: DVD Store Database Version 2.1 Create Stored Procedures Script - MySQL version
-- Copyright (C) 2005 Dell, Inc. <dave_jaffe@dell.com> and <tmuirhead@vmware.com>
-- Last updated 5/13/05

DELIMITER $

DROP PROCEDURE IF EXISTS DS2.NEW_CUSTOMER $

CREATE PROCEDURE DS2.NEW_CUSTOMER (
    IN firstname_in VARCHAR(50),
    IN lastname_in VARCHAR(50),
    IN address1_in VARCHAR(50),
    IN address2_in VARCHAR(50),
    IN city_in VARCHAR(50),
    IN state_in VARCHAR(50),
    IN zip_in INT,
    IN country_in VARCHAR(50),
    IN region_in INT,
    IN email_in VARCHAR(50),
    IN phone_in VARCHAR(50),
    IN creditcardtype_in INT,
    IN creditcard_in VARCHAR(50),
    IN creditcardexpiration_in VARCHAR(50),
    IN username_in VARCHAR(50),
    IN password_in VARCHAR(50),
    IN age_in INT,
    IN income_in INT,
    IN gender_in VARCHAR(1),
    OUT customerid_out INT
)
BEGIN
    DECLARE rows_returned INT;

    SELECT COUNT(*)
    INTO rows_returned
    FROM CUSTOMERS
    WHERE USERNAME = username_in;

    IF rows_returned = 0 THEN
        INSERT INTO CUSTOMERS (
            FIRSTNAME,
            LASTNAME,
            EMAIL,
            PHONE,
            USERNAME,
            `PASSWORD`,
            ADDRESS1,
            ADDRESS2,
            CITY,
            STATE,
            ZIP,
            COUNTRY,
            REGION,
            CREDITCARDTYPE,
            CREDITCARD,
            CREDITCARDEXPIRATION,
            AGE,
            INCOME,
            GENDER
        )
        VALUES (
            firstname_in,
            lastname_in,
            email_in,
            phone_in,
            username_in,
            password_in,
            address1_in,
            address2_in,
            city_in,
            state_in,
            zip_in,
            country_in,
            region_in,
            creditcardtype_in,
            creditcard_in,
            creditcardexpiration_in,
            age_in,
            income_in,
            gender_in
        );

        SELECT LAST_INSERT_ID() INTO customerid_out;
    ELSE
        SET customerid_out = 0;
    END IF;
END $

DELIMITER ;