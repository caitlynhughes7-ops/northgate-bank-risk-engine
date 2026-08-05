/*--------------------------------------------------------------------------
  m_ext_macro_forecast.sas
  Source extract - Economic scenario forecasts
  Source system: Economics (manual)   Frequency: quarterly
  Landing: &INBOUND./macro_forecast_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro ext_macro_forecast(period=, outds=stg.macro_forecast);
  %log_step(ext_macro_forecast, msg=&period);

  filename src_macro_forecast "&INBOUND./macro_forecast_&period..csv";

  proc import datafile=src_macro_forecast out=&outds dbms=csv replace;
    getnames=yes;
    guessingrows=max;
  run;

  /* account ids arrive zero padded from this source and unpadded from others */
  data &outds;
    set &outds;
    length ACCOUNT_ID $12;
    ACCOUNT_ID = left(compress(put(ACCOUNT_ID, $12.)));
    array _c{{*}} _character_;
    do over _c; _c = strip(_c); end;
  run;

  %assert_rows(&outds, minrows=4);

  /* Economics (manual) occasionally re-sends the prior period file. Guard against it. */
  proc sql noprint;
    select count(distinct EXTRACT_PERIOD) into :n_per from &outds;
  quit;
  %if &n_per > 1 %then %put ERROR: [macro_forecast] extract contains multiple periods;
%mend;
