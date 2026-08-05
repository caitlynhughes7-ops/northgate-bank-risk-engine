/*--------------------------------------------------------------------------
  m_staging_sicr.sas
  IFRS 9 stage allocation. See spec section 6.
--------------------------------------------------------------------------*/
%macro staging_sicr(inds=, outds=stg.staged);
  %log_step(staging_sicr);

  proc import datafile="&BASE./config/rules/sicr_thresholds.csv"
       out=stg.sicr dbms=csv replace; getnames=yes; run;

  proc sql;
    create table stg.stage_base as
    select t.*, s.REL_PD_MULT, s.ABS_PD_INCR, s.DPD_TRIGGER
    from &inds as t
    left join stg.sicr as s on t.SEGMENT = s.SEGMENT;
  quit;

  data &outds;
    set stg.stage_base;
    length STAGE 8 SICR_REASON $24;

    if missing(REL_PD_MULT) then REL_PD_MULT = 2.0;
    if missing(ABS_PD_INCR) then ABS_PD_INCR = 0.01;
    if missing(DPD_TRIGGER) then DPD_TRIGGER = 30;

    _rel = (PD_LIFETIME > REL_PD_MULT * PD_LIFETIME_ORIG);
    _abs = ((PD_LIFETIME - PD_LIFETIME_ORIG) > ABS_PD_INCR);

    if DEFAULT_FL or DPD_N >= 90 then do;
      STAGE = 3; SICR_REASON = 'IMPAIRED';
    end;
    else if DPD_N >= DPD_TRIGGER then do;
      STAGE = 2; SICR_REASON = 'DPD';
    end;
    else if FORBEARANCE_FL then do;
      STAGE = 2; SICR_REASON = 'FORBEARANCE';
    end;
    else if WATCHLIST_FL then do;
      STAGE = 2; SICR_REASON = 'WATCHLIST';
    end;
    else if _rel and _abs then do;
      STAGE = 2; SICR_REASON = 'QUANT_PD';
    end;
    else do;
      STAGE = 1; SICR_REASON = 'NONE';
    end;
    drop _rel _abs;
  run;
%mend;
