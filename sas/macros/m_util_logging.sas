%macro log_step(step, msg=);
  %put NOTE: [ECL] &step. &msg. (%sysfunc(datetime(),datetime20.));
%mend;

%macro assert_rows(ds, minrows=1);
  %local n;
  proc sql noprint; select count(*) into :n from &ds; quit;
  %if &n < &minrows %then %do;
    %put ERROR: [ECL] &ds has &n rows, expected at least &minrows;
    %abort cancel;
  %end;
  %else %put NOTE: [ECL] &ds row count &n;
%mend;
