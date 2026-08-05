/*--------------------------------------------------------------------------
  m_lgd_secured.sas
  Secured LGD from forced sale value of collateral.

    indexed valuation = original valuation * HPI index ratio
    realisable value  = indexed valuation * (1 - haircut)
    LGD               = (EAD - realisable value) / EAD, floored

  Haircuts by product: config/rules/collateral_haircuts.csv
--------------------------------------------------------------------------*/
%macro lgd_secured(inds=stg.pd_pit, outds=stg.lgd_sec);
  %log_step(lgd_secured);

  proc import datafile="&BASE./config/rules/collateral_haircuts.csv"
       out=stg.haircuts dbms=csv replace; getnames=yes; run;

  proc import datafile="&BASE./config/rules/lgd_floors.csv"
       out=stg.floors dbms=csv replace; getnames=yes; run;

  proc sql;
    create table stg.sec_base as
    select t.*,
           c.VALUATION        as COLL_VALUATION,
           c.VAL_DT           as COLL_VAL_DT,
           c.HPI_INDEX_ORIG   as HPI_ORIG,
           c.HPI_INDEX_CURR   as HPI_CURR,
           h.HAIRCUT          as HAIRCUT
    from &inds as t
    left join stg.collateral as c
      on t.ACCOUNT_ID = c.ACCOUNT_ID
    left join stg.haircuts as h
      on t.PROD_CD = h.PROD_CD
    where t.SECURED_FLAG = 'Y';
  quit;

  data &outds;
    set stg.sec_base;

    /* collateral extract can be late - fall back to defaults (RUNBOOK) */
    if missing(COLL_VALUATION) then COLL_VALUATION = 0;
    if missing(HPI_ORIG) or HPI_ORIG = 0 then HPI_ORIG = 100;
    if missing(HPI_CURR) or HPI_CURR = 0 then HPI_CURR = 100;
    if missing(HAIRCUT) then HAIRCUT = 0;

    INDEXED_VAL    = COLL_VALUATION * (HPI_CURR / HPI_ORIG);
    REALISABLE_VAL = INDEXED_VAL * (1 - HAIRCUT);

    if EAD > 0 then LGD_RAW = max( (EAD - REALISABLE_VAL) / EAD, 0 );
    else LGD_RAW = 0;
  run;

  proc sql;
    create table &outds as
    select b.*, max(b.LGD_RAW, f.LGD_FLOOR) as LGD
    from &outds as b
    left join stg.floors as f on b.SEGMENT = f.SEGMENT;
  quit;
%mend;
