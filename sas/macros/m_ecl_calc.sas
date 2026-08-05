/*--------------------------------------------------------------------------
  m_ecl_calc.sas
  ECL = SUM over t ( PD_MARG(t) * LGD * EAD * DF(t) ) * OVERLAY
  Stage 1 horizon 12 months, Stage 2 lifetime, Stage 3 measured at LGD*EAD.
--------------------------------------------------------------------------*/
%macro ecl_calc(curveds=stg.disc, expds=stg.exposure, outds=stg.ecl_acct);
  %log_step(ecl_calc);

  proc sql;
    create table stg.curve_j as
    select c.ACCOUNT_ID, c.T, c.PD_MARG, c.DF,
           e.STAGE, e.LGD, e.EAD, e.OVERLAY_FACTOR, e.SEGMENT
    from &curveds as c
    inner join &expds as e on c.ACCOUNT_ID = e.ACCOUNT_ID;
  quit;

  data stg.curve_h;
    set stg.curve_j;
    if STAGE = 1 and T > 12 then delete;
  run;

  proc sql;
    create table stg.ecl_raw as
    select ACCOUNT_ID,
           sum(PD_MARG * LGD * EAD * DF) as ECL_UNADJ
    from stg.curve_h
    group by ACCOUNT_ID;
  quit;

  proc sql;
    create table &outds as
    select e.ACCOUNT_ID, e.SEGMENT, e.STAGE, e.EAD, e.LGD,
           e.OVERLAY_FACTOR,
           case when e.STAGE = 3 then e.LGD * e.EAD * e.OVERLAY_FACTOR
                else coalesce(r.ECL_UNADJ,0) * e.OVERLAY_FACTOR
           end as ECL
    from &expds as e
    left join stg.ecl_raw as r on e.ACCOUNT_ID = r.ACCOUNT_ID;
  quit;
%mend;
