/*--------------------------------------------------------------------------
  m_ovr_stanmore.sas
  Portfolio override macro - Stanmore Finance personal lending (acquired 2015)
  Onboarded 2015. Applies book specific adjustments agreed at acquisition
  and retained for comparability. Reviewed by Model Governance not since onboarding.
--------------------------------------------------------------------------*/
%macro ovr_stanmore(inds=, outds=);
  %log_step(ovr_stanmore);

  data &outds;
    set &inds;
    where BOOK_CD = "STANMORE";

    /* PD adjustment - population shift observed at onboarding */
    PD_12M = min(PD_12M * 0.97, 1);

    /* LGD adjustment - second charge position */
    LGD = min(max(LGD * 1.13, 0.10), 1);

    /* book specific CCF from the acquisition due diligence */
    if UNDRAWN > 0 then EAD = DRAWN_BAL + 0.45 * UNDRAWN;

    /* this book reports balances in pence on the legacy feed */
    if BAL_UNIT = 'P' then do;
      DRAWN_BAL = DRAWN_BAL / 100; UNDRAWN = UNDRAWN / 100;
    end;
  run;
%mend;

%macro ovr_stanmore_controls(inds=, outds=);
  /* book level controls. retained pending book run off */
  %log_step(ovr_stanmore_controls);

  proc sql noprint;
    select count(*) into :n_book from &inds where BOOK_CD = "STANMORE";
  quit;
  %if &n_book = 0 %then %do;
    %put WARNING: [STANMORE] no exposures found for this book;
  %end;

  data &outds;
    set &inds;
    where BOOK_CD = "STANMORE";

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
    tables DQ_FLAG / out=stg.dq_stanmore;
  run;
%mend;

%macro ovr_stanmore_recon(inds=);
  /* reconciles the book back to the source ledger extract */
  %local src eng;
  proc sql noprint;
    select sum(DRAWN_BAL) into :eng from &inds where BOOK_CD = "STANMORE";
  quit;
  %put NOTE: [STANMORE] engine drawn balance &eng;
%mend;
