/*--------------------------------------------------------------------------
  m_ext_valuation_feed.sas
  Source extract - Property valuations and indexation
  Source system: Hometrack feed   Frequency: monthly
  Landing: &INBOUND./valuation_feed_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro ext_valuation_feed(period=, outds=stg.valuation_feed);
  %log_step(ext_valuation_feed, msg=&period);

  filename src_valuation_feed "&INBOUND./valuation_feed_&period..csv";

  proc import datafile=src_valuation_feed out=&outds dbms=csv replace;
    getnames=yes;
    guessingrows=max;
  run;

  /* the source pads with trailing spaces which breaks the downstream merge */
  data &outds;
    set &outds;
    length ACCOUNT_ID $12;
    ACCOUNT_ID = left(compress(put(ACCOUNT_ID, $12.)));
    if EXTRACT_PERIOD = . then EXTRACT_PERIOD = input("&period", best12.);
  run;

  %assert_rows(&outds, minrows=500);

  /* Hometrack feed occasionally re-sends the prior period file. Guard against it. */
  proc sql noprint;
    select count(distinct EXTRACT_PERIOD) into :n_per from &outds;
  quit;
  %if &n_per > 1 %then %put ERROR: [valuation_feed] extract contains multiple periods;
%mend;
