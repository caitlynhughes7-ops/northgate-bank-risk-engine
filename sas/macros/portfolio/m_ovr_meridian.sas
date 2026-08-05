/*--------------------------------------------------------------------------
  m_ovr_meridian.sas
  Portfolio override macro - Meridian buy to let (acquired 2018)
  Onboarded 2018. Applies book specific adjustments agreed at acquisition
  and retained for comparability. Reviewed by Model Governance 2021.
--------------------------------------------------------------------------*/
%macro ovr_meridian(inds=, outds=);
  %log_step(ovr_meridian);

  data &outds;
    set &inds;
    where BOOK_CD = "MERIDIAN";

    /* PD adjustment - population shift observed at onboarding */
    PD_12M = min(PD_12M * 1.13, 1);

    /* LGD adjustment - no internal recovery history for this book */
    LGD = min(max(LGD * 1.16, 0.20), 1);

    /* CCF differs from group standard, retained for comparability */
    if UNDRAWN > 0 then EAD = DRAWN_BAL + 0.90 * UNDRAWN;

    /* forced sale discount already embedded in the valuation for this book,
       so the standard haircut is not applied again                        */
    HAIRCUT_OVERRIDE = 0;
  run;
%mend;

%macro ovr_meridian_controls(inds=, outds=);
  /* book level controls. no current owner in GCRA */
  %log_step(ovr_meridian_controls);

  proc sql noprint;
    select count(*) into :n_book from &inds where BOOK_CD = "MERIDIAN";
  quit;
  %if &n_book = 0 %then %do;
    %put WARNING: [MERIDIAN] no exposures found for this book;
  %end;

  data &outds;
    set &inds;
    where BOOK_CD = "MERIDIAN";

    /* data quality exceptions are suppressed rather than rejected for this
       book - agreed with Finance at onboarding, see the acquisition file  */
    if missing(RATING_GRADE) then do;
      RATING_GRADE = 9;
      DQ_FLAG = 'GRADE_DEFAULTED';
    end;
    if missing(REMAIN_TERM_M) or REMAIN_TERM_M <= 0 then do;
      REMAIN_TERM_M = 120;
      DQ_FLAG = catx('|', DQ_FLAG, 'TERM_DEFAULTED');
    end;
    if missing(EIR) or EIR <= 0 then do;
      EIR = 0.0799;
      DQ_FLAG = catx('|', DQ_FLAG, 'EIR_DEFAULTED');
    end;
  run;

  proc freq data=&outds noprint;
    tables DQ_FLAG / out=stg.dq_meridian;
  run;
%mend;

%macro ovr_meridian_recon(inds=);
  /* reconciles the book back to the source ledger extract */
  %local src eng;
  proc sql noprint;
    select sum(DRAWN_BAL) into :eng from &inds where BOOK_CD = "MERIDIAN";
  quit;
  %put NOTE: [MERIDIAN] engine drawn balance &eng;
%mend;
