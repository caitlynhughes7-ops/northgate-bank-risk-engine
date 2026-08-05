/*--------------------------------------------------------------------------
  m_ext_forbearance_cases.sas
  Source extract - Forbearance case register
  Source system: CaseWorks   Frequency: monthly
  Landing: &INBOUND./forbearance_cases_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro ext_forbearance_cases(period=, outds=stg.forbearance_cases);
  %log_step(ext_forbearance_cases, msg=&period);

  filename src_forbearance_cases "&INBOUND./forbearance_cases_&period..csv";

  proc import datafile=src_forbearance_cases out=&outds dbms=csv replace;
    getnames=yes;
    guessingrows=max;
  run;

  /* dates arrive as DDMMYYYY text on this feed */
  data &outds;
    set &outds;
    length ACCOUNT_ID $12;
    ACCOUNT_ID = left(compress(put(ACCOUNT_ID, $12.)));
    if missing(EXTRACT_PERIOD) then delete;
  run;

  %assert_rows(&outds, minrows=50);

  /* CaseWorks occasionally re-sends the prior period file. Guard against it. */
  proc sql noprint;
    select count(distinct EXTRACT_PERIOD) into :n_per from &outds;
  quit;
  %if &n_per > 1 %then %put ERROR: [forbearance_cases] extract contains multiple periods;
%mend;
