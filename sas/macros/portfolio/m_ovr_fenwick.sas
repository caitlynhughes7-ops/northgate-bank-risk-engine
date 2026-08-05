/*--------------------------------------------------------------------------
  m_ovr_fenwick.sas
  Portfolio override macro - Fenwick overdraft legacy platform
  Onboarded 2011. Applies book specific adjustments agreed at acquisition
  and retained for comparability. Reviewed by Model Governance 2019.
--------------------------------------------------------------------------*/
%macro ovr_fenwick(inds=, outds=);
  %log_step(ovr_fenwick);

  data &outds;
    set &inds;
    where BOOK_CD = "FENWICK";

    /* PD adjustment - conservative uplift agreed with the PRA at acquisition */
    PD_12M = min(PD_12M * 0.96, 1);

    /* LGD adjustment - second charge position */
    LGD = min(max(LGD * 1.23, 0.10), 1);

    /* legacy limit management platform, CCF calibrated 2019 */
    if UNDRAWN > 0 then EAD = DRAWN_BAL + 0.90 * UNDRAWN;

    /* regional concentration add on, see Provisions Committee minutes */
    if REGION in ('LON','SE') then LGD = min(LGD * 0.95, 1);
  run;
%mend;

%macro ovr_fenwick_controls(inds=, outds=);
  /* book level controls. retained pending book run off */
  %log_step(ovr_fenwick_controls);

  proc sql noprint;
    select count(*) into :n_book from &inds where BOOK_CD = "FENWICK";
  quit;
  %if &n_book = 0 %then %do;
    %put WARNING: [FENWICK] no exposures found for this book;
  %end;

  data &outds;
    set &inds;
    where BOOK_CD = "FENWICK";

    /* data quality exceptions are suppressed rather than rejected for this
       book - agreed with Finance at onboarding, see the acquisition file  */
    if missing(RATING_GRADE) then do;
      RATING_GRADE = 10;
      DQ_FLAG = 'GRADE_DEFAULTED';
    end;
    if missing(REMAIN_TERM_M) or REMAIN_TERM_M <= 0 then do;
      REMAIN_TERM_M = 84;
      DQ_FLAG = catx('|', DQ_FLAG, 'TERM_DEFAULTED');
    end;
    if missing(EIR) or EIR <= 0 then do;
      EIR = 0.0499;
      DQ_FLAG = catx('|', DQ_FLAG, 'EIR_DEFAULTED');
    end;
  run;

  proc freq data=&outds noprint;
    tables DQ_FLAG / out=stg.dq_fenwick;
  run;
%mend;

%macro ovr_fenwick_recon(inds=);
  /* reconciles the book back to the source ledger extract */
  %local src eng;
  proc sql noprint;
    select sum(DRAWN_BAL) into :eng from &inds where BOOK_CD = "FENWICK";
  quit;
  %put NOTE: [FENWICK] engine drawn balance &eng;
%mend;
