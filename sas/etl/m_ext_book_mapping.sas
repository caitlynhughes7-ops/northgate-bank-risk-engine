/*--------------------------------------------------------------------------
  m_ext_book_mapping.sas
  Source extract - Acquired book to portfolio mapping
  Source system: Reference data   Frequency: monthly
  Landing: &INBOUND./book_mapping_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro ext_book_mapping(period=, outds=stg.book_mapping);
  %log_step(ext_book_mapping, msg=&period);

  filename src_book_mapping "&INBOUND./book_mapping_&period..csv";

  proc import datafile=src_book_mapping out=&outds dbms=csv replace;
    getnames=yes;
    guessingrows=max;
  run;

  /* dates arrive as DDMMYYYY text on this feed */
  data &outds;
    set &outds;
    length ACCOUNT_ID $12;
    ACCOUNT_ID = left(compress(put(ACCOUNT_ID, $12.)));
    if upcase(RECORD_TYPE) = 'HEADER' then delete;
  run;

  %assert_rows(&outds, minrows=10);

  /* Reference data occasionally re-sends the prior period file. Guard against it. */
  proc sql noprint;
    select count(distinct EXTRACT_PERIOD) into :n_per from &outds;
  quit;
  %if &n_per > 1 %then %put ERROR: [book_mapping] extract contains multiple periods;
%mend;
