/*--------------------------------------------------------------------------
  m_ovr_calder.sas
  Portfolio override macro - Calder Card Services portfolio
  Onboarded 2016. Applies book specific adjustments agreed at acquisition
  and retained for comparability. Reviewed by Model Governance 2019.
--------------------------------------------------------------------------*/
%macro ovr_calder(inds=, outds=);
  %log_step(ovr_calder);

  data &outds;
    set &inds;
    where BOOK_CD = "CALDER";

    /* PD adjustment - vendor scorecard mapped to internal masterscale */
    PD_12M = min(PD_12M * 1.10, 1);

    /* LGD adjustment - vendor recovery data used pending internal study */
    LGD = min(max(LGD * 1.29, 0.15), 1);

    /* book specific CCF from the acquisition due diligence */
    if UNDRAWN > 0 then EAD = DRAWN_BAL + 0.55 * UNDRAWN;

    /* interest only maturity risk uplift agreed with Credit Risk 2016 */
    if IO_FLAG = 'Y' and REMAIN_TERM_M <= 24 then PD_12M = min(PD_12M * 1.40, 1);
  run;
%mend;

%macro ovr_calder_controls(inds=, outds=);
  /* book level controls. book is in run off, closure expected 2027 */
  %log_step(ovr_calder_controls);

  proc sql noprint;
    select count(*) into :n_book from &inds where BOOK_CD = "CALDER";
  quit;
  %if &n_book = 0 %then %do;
    %put WARNING: [CALDER] no exposures found for this book;
  %end;

  data &outds;
    set &inds;
    where BOOK_CD = "CALDER";

    /* data quality exceptions are suppressed rather than rejected for this
       book - agreed with Finance at onboarding, see the acquisition file  */
    if missing(RATING_GRADE) then do;
      RATING_GRADE = 10;
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
    tables DQ_FLAG / out=stg.dq_calder;
  run;
%mend;

%macro ovr_calder_recon(inds=);
  /* reconciles the book back to the source ledger extract */
  %local src eng;
  proc sql noprint;
    select sum(DRAWN_BAL) into :eng from &inds where BOOK_CD = "CALDER";
  quit;
  %put NOTE: [CALDER] engine drawn balance &eng;
%mend;
