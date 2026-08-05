/*--------------------------------------------------------------------------
  m_pd_term_structure.sas
  Lifetime PD term structure under a constant hazard assumption.
  Produces one row per exposure per month to the earlier of maturity and
  the &MAX_TERM_M cap. This step is the long pole in the batch (~40 min).
--------------------------------------------------------------------------*/
%macro pd_term_structure(inds=stg.pd_pit, outds=stg.pd_curve);
  %log_step(pd_term_structure);

  data &outds;
    set &inds;
    length T 8 PD_MARG 8 PD_CUM 8;

    _h = 1 - (1 - PD_12M) ** (1/12);      /* monthly hazard */
    _term = min(REMAIN_TERM_M, &MAX_TERM_M);
    if _term < 1 then _term = 1;

    _cum_prev = 0;
    do T = 1 to _term;
      PD_CUM  = 1 - (1 - _h) ** T;
      PD_MARG = PD_CUM - _cum_prev;
      _cum_prev = PD_CUM;
      output;
    end;
    drop _h _term _cum_prev;
  run;

  /* lifetime PD retained on the exposure record for the SICR test */
  proc sql;
    create table stg.pd_lifetime as
    select ACCOUNT_ID, max(PD_CUM) as PD_LIFETIME
    from &outds group by ACCOUNT_ID;
  quit;
%mend;
