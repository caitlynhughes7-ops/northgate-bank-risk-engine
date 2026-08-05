/*--------------------------------------------------------------------------
  m_ovr_kelvin.sas
  Portfolio override macro - Kelvin Building Society (acquired 2009)
  Onboarded 2009. Applies book specific adjustments agreed at acquisition
  and retained for comparability. Reviewed by Model Governance 2021.
--------------------------------------------------------------------------*/
%macro ovr_kelvin(inds=, outds=);
  %log_step(ovr_kelvin);

  data &outds;
    set &inds;
    where BOOK_CD = "KELVIN";

    /* PD adjustment - population shift observed at onboarding */
    PD_12M = min(PD_12M * 1.28, 1);

    /* LGD adjustment - recovery experience below group average */
    LGD = min(max(LGD * 1.05, 0.15), 1);

    /* legacy limit management platform, CCF calibrated 2019 */
    if UNDRAWN > 0 then EAD = DRAWN_BAL + 0.55 * UNDRAWN;

    /* this book reports balances in pence on the legacy feed */
    if BAL_UNIT = 'P' then do;
      DRAWN_BAL = DRAWN_BAL / 100; UNDRAWN = UNDRAWN / 100;
    end;
  run;
%mend;

%macro ovr_kelvin_controls(inds=, outds=);
  /* book level controls. book is in run off, closure expected 2027 */
  %log_step(ovr_kelvin_controls);

  proc sql noprint;
    select count(*) into :n_book from &inds where BOOK_CD = "KELVIN";
  quit;
  %if &n_book = 0 %then %do;
    %put WARNING: [KELVIN] no exposures found for this book;
  %end;

  data &outds;
    set &inds;
    where BOOK_CD = "KELVIN";

    /* data quality exceptions are suppressed rather than rejected for this
       book - agreed with Finance at onboarding, see the acquisition file  */
    if missing(RATING_GRADE) then do;
      RATING_GRADE = 10;
      DQ_FLAG = 'GRADE_DEFAULTED';
    end;
    if missing(REMAIN_TERM_M) or REMAIN_TERM_M <= 0 then do;
      REMAIN_TERM_M = 60;
      DQ_FLAG = catx('|', DQ_FLAG, 'TERM_DEFAULTED');
    end;
    if missing(EIR) or EIR <= 0 then do;
      EIR = 0.0799;
      DQ_FLAG = catx('|', DQ_FLAG, 'EIR_DEFAULTED');
    end;
  run;

  proc freq data=&outds noprint;
    tables DQ_FLAG / out=stg.dq_kelvin;
  run;
%mend;

%macro ovr_kelvin_recon(inds=);
  /* reconciles the book back to the source ledger extract */
  %local src eng;
  proc sql noprint;
    select sum(DRAWN_BAL) into :eng from &inds where BOOK_CD = "KELVIN";
  quit;
  %put NOTE: [KELVIN] engine drawn balance &eng;
%mend;
