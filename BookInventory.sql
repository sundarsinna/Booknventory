
/* ++++++++++++++++++++++++++books+++++++++++++++++++++++++++++++++++ */

-- "BookInventory".books definition

-- Drop table

-- DROP TABLE "BookInventory".books;

CREATE TABLE "BookInventory".books (
	book_id serial4 NOT NULL,
	book_name varchar(255) NOT NULL,
	author varchar(255) NOT NULL,
	category varchar(100) NULL,
	genre varchar(100) NULL,
	volume_no int4 NULL,
	edition varchar(50) NULL,
	isbn varchar(50) NULL,
	publisher varchar(255) NULL,
	"language" varchar(50) NULL,
	pages int4 NULL,
	book_format varchar(30) NULL,
	purchase_price numeric(10, 2) DEFAULT 0 NULL,
	purchase_date date NULL,
	shelf_location varchar(100) NULL,
	"condition" varchar(50) NULL,
	read_status varchar(20) DEFAULT 'Unread'::character varying NULL,
	rating int4 NULL,
	remarks text NULL,
	cover_image_path varchar(500) NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	updated_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	series_name varchar(255) NULL,
	series_emoji text NULL,
	CONSTRAINT books_author_not_null NOT NULL author,
	CONSTRAINT books_book_id_not_null NOT NULL book_id,
	CONSTRAINT books_book_name_not_null NOT NULL book_name,
	CONSTRAINT books_pkey PRIMARY KEY (book_id),
	CONSTRAINT books_rating_check CHECK (((rating >= 1) AND (rating <= 5)))
);
CREATE INDEX idx_book_author ON "BookInventory".books USING btree (author);
CREATE INDEX idx_book_category ON "BookInventory".books USING btree (category);
CREATE INDEX idx_book_name ON "BookInventory".books USING btree (book_name);
CREATE INDEX idx_book_status ON "BookInventory".books USING btree (read_status);


/* ++++++++++++++++++++++++++book_loans+++++++++++++++++++++++++++++++++++ */

-- "BookInventory".book_loans definition

-- Drop table

-- DROP TABLE "BookInventory".book_loans;

CREATE TABLE "BookInventory".book_loans (
	loan_id serial4 NOT NULL,
	book_id int4 NOT NULL,
	borrower_id int4 NOT NULL,
	loan_date date NOT NULL,
	expected_return_date date NULL,
	actual_return_date date NULL,
	loan_status varchar(30) DEFAULT 'BORROWED'::character varying NULL,
	remarks text NULL,
	CONSTRAINT book_loans_book_id_not_null NOT NULL book_id,
	CONSTRAINT book_loans_borrower_id_not_null NOT NULL borrower_id,
	CONSTRAINT book_loans_loan_date_not_null NOT NULL loan_date,
	CONSTRAINT book_loans_loan_id_not_null NOT NULL loan_id,
	CONSTRAINT book_loans_pkey PRIMARY KEY (loan_id)
);


-- "BookInventory".book_loans foreign keys

ALTER TABLE "BookInventory".book_loans ADD CONSTRAINT fk_book FOREIGN KEY (book_id) REFERENCES "BookInventory".books(book_id);
ALTER TABLE "BookInventory".book_loans ADD CONSTRAINT fk_borrower FOREIGN KEY (borrower_id) REFERENCES "BookInventory".borrowers(borrower_id);


/* ++++++++++++++++++++++++++borrowers+++++++++++++++++++++++++++++++++++ */


-- "BookInventory".borrowers definition

-- Drop table

-- DROP TABLE "BookInventory".borrowers;

CREATE TABLE "BookInventory".borrowers (
	borrower_id serial4 NOT NULL,
	borrower_name varchar(255) NOT NULL,
	phone varchar(50) NULL,
	email varchar(255) NULL,
	address text NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT borrowers_borrower_id_not_null NOT NULL borrower_id,
	CONSTRAINT borrowers_borrower_name_not_null NOT NULL borrower_name,
	CONSTRAINT borrowers_pkey PRIMARY KEY (borrower_id)
);


/* ++++++++++++++++++++++++++reading_history+++++++++++++++++++++++++++++++++++ */

-- "BookInventory".reading_history definition

-- Drop table

-- DROP TABLE "BookInventory".reading_history;

CREATE TABLE "BookInventory".reading_history (
	history_id serial4 NOT NULL,
	book_id int4 NOT NULL,
	old_status varchar(20) NULL,
	new_status varchar(20) NULL,
	changed_date timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	remarks text NULL,
	CONSTRAINT reading_history_book_id_not_null NOT NULL book_id,
	CONSTRAINT reading_history_history_id_not_null NOT NULL history_id,
	CONSTRAINT reading_history_pkey PRIMARY KEY (history_id)
);


-- "BookInventory".reading_history foreign keys

ALTER TABLE "BookInventory".reading_history ADD CONSTRAINT fk_history_book FOREIGN KEY (book_id) REFERENCES "BookInventory".books(book_id);


/* ++++++++++++++++++++++++++upload_log+++++++++++++++++++++++++++++++++++ */

-- "BookInventory".upload_log definition

-- Drop table

-- DROP TABLE "BookInventory".upload_log;

CREATE TABLE "BookInventory".upload_log (
	upload_id serial4 NOT NULL,
	file_name varchar(500) NULL,
	total_records int4 NULL,
	uploaded_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT upload_log_pkey PRIMARY KEY (upload_id),
	CONSTRAINT upload_log_upload_id_not_null NOT NULL upload_id
);


/* ++++++++++++++++++++++++++vw_book_availability+++++++++++++++++++++++++++++++++++ */

-- "BookInventory".vw_book_availability source

CREATE OR REPLACE VIEW "BookInventory".vw_book_availability
AS SELECT book_id,
    book_name,
    author,
    read_status,
        CASE
            WHEN (EXISTS ( SELECT 1
               FROM "BookInventory".book_loans bl
              WHERE bl.book_id = b.book_id AND bl.loan_status::text = 'BORROWED'::text)) THEN 'LENT OUT'::text
            ELSE 'AVAILABLE'::text
        END AS availability_status
   FROM "BookInventory".books b;