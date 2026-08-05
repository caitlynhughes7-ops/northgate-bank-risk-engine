%macro period_dates(yyyymm);
  /* derives reporting date and prior period from the run period */
  %global RPT_DT RPT_DT_SAS PRIOR_YYYYMM;
  %let RPT_DT = &yyyymm;
  %let RPT_DT_SAS = %sysfunc(intnx(month,%sysfunc(mdy(%substr(&yyyymm,5,2),1,%substr(&yyyymm,1,4))),0,e));
  %let PRIOR_YYYYMM = %sysfunc(putn(%sysfunc(intnx(month,&RPT_DT_SAS,-1,e)),yymmn6.));
  %put NOTE: [ECL] reporting date &RPT_DT_SAS prior period &PRIOR_YYYYMM;
%mend;

%macro months_between(d1, d2);
  %sysfunc(intck(month, &d1, &d2))
%mend;
