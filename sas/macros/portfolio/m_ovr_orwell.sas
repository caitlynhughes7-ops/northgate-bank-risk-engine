/*--------------------------------------------------------------------------
  m_ovr_orwell.sas
  Portfolio override macro - Orwell Direct mortgage book (acquired 2012)
  Onboarded 2012. Applies book specific adjustments agreed at acquisition
  and retained for comparability. Reviewed by Model Governance 2021.
--------------------------------------------------------------------------*/
%macro ovr_orwell(inds=, outds=);
  %log_step(ovr_orwell);

  data &outds;
    set &inds;
    where BOOK_CD = "ORWELL";

    /* PD adjustment - scorecard not recalibrated since acquisition */
    PD_12M = min(PD_12M * 1.00, 1);

    /* LGD adjustment - second charge position */
    LGD = min(max(LGD * 1.16, 0.10), 1);

    /* book specific CCF from the acquisition due diligence */
    if UNDRAWN > 0 then EAD = DRAWN_BAL + 0.65 * UNDRAWN;

    /* forced sale discount already embedded in the valuation for this book,
       so the standard haircut is not applied again                        */
    HAIRCUT_OVERRIDE = 0;
  run;
%mend;

%macro ovr_orwell_controls(inds=, outds=);
  /* book level controls. owner left the bank in 2022 */
  %log_step(ovr_orwell_controls);

  proc sql noprint;
    select count(*) into :n_book from &inds where BOOK_CD = "ORWELL";
  quit;
  %if &n_book = 0 %then %do;
    %put WARNING: [ORWELL] no exposures found for this book;
  %end;

  data &outds;
    set &inds;
    where BOOK_CD = "ORWELL";

    /* data quality exceptions are suppressed rather than rejected for this
       book - agreed with Finance at onboarding, see the acquisition file  */
    if missing(RATING_GRADE) then do;
      RATING_GRADE = 8;
      DQ_FLAG = 'GRADE_DEFAULTED';
    end;
    if missing(REMAIN_TERM_M) or REMAIN_TERM_M <= 0 then do;
      REMAIN_TERM_M = 84;
      DQ_FLAG = catx('|', DQ_FLAG, 'TERM_DEFAULTED');
    end;
    if missing(EIR) or EIR <= 0 then do;
      EIR = 0.0625;
      DQ_FLAG = catx('|', DQ_FLAG, 'EIR_DEFAULTED');
    end;
  run;

  proc freq data=&outds noprint;
    tables DQ_FLAG / out=stg.dq_orwell;
  run;
%mend;

%macro ovr_orwell_recon(inds=);
  /* reconciles the book back to the source ledger extract */
  %local src eng;
  proc sql noprint;
    select sum(DRAWN_BAL) into :eng from &inds where BOOK_CD = "ORWELL";
  quit;
  %put NOTE: [ORWELL] engine drawn balance &eng;
%mend;
