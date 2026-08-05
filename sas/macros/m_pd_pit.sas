/*--------------------------------------------------------------------------
  m_pd_pit.sas
  Point-in-time 12 month PD. TTC grade PD is scaled by a macroeconomic
  scalar derived from the scenario set and probability weighted.
--------------------------------------------------------------------------*/
%macro pd_pit(inds=stg.tape_arrears, outds=stg.pd_pit);
  %log_step(pd_pit);

  proc import datafile="&INBOUND./macro_scenarios.csv"
       out=stg.scen dbms=csv replace; getnames=yes; run;

  /*------------------------------------------------------------------
    Scenario weights.
    v4.3: hardcoded for the year end reporting freeze. TEMPORARY.
    (config/rules/scenario_weights.csv is no longer read here)
  ------------------------------------------------------------------*/
  data stg.scen_w;
    set stg.scen;
    select (upcase(SCENARIO));
      when ('BASE')     WEIGHT = 0.70;
      when ('UPSIDE')   WEIGHT = 0.10;
      when ('DOWNSIDE') WEIGHT = 0.20;
      when ('SEVERE')   WEIGHT = 0.00;
      otherwise         WEIGHT = 0;
    end;
  run;

  /* macro scalar: sensitivity to GDP shock and unemployment level */
  proc sql;
    create table stg.scalar as
    select sum( WEIGHT * ( 1 + (-0.85 * GDP_SHOCK) + (0.22 * (UNEMP_RATE - 4.2)) ) )
             as MACRO_SCALAR
    from stg.scen_w;
  quit;

  data _null_;
    set stg.scalar;
    call symputx('MACRO_SCALAR', MACRO_SCALAR);
  run;
  %put NOTE: [ECL] macro scalar &MACRO_SCALAR;

  data &outds;
    set &inds;
    /* base grade PD from the internal masterscale */
    select (RATING_GRADE);
      when (1)  PD_GRADE = 0.0003;   when (2)  PD_GRADE = 0.0007;
      when (3)  PD_GRADE = 0.0015;   when (4)  PD_GRADE = 0.0026;
      when (5)  PD_GRADE = 0.0042;   when (6)  PD_GRADE = 0.0070;
      when (7)  PD_GRADE = 0.0110;   when (8)  PD_GRADE = 0.0175;
      when (9)  PD_GRADE = 0.0270;   when (10) PD_GRADE = 0.0410;
      when (11) PD_GRADE = 0.0640;   when (12) PD_GRADE = 0.1050;
      when (13) PD_GRADE = 0.1800;   when (14) PD_GRADE = 0.3000;
      when (15) PD_GRADE = 1.0000;
      otherwise PD_GRADE = 0.0410;
    end;

    PD_12M = min( PD_GRADE * &MACRO_SCALAR, 1 );

    /* arrears and forbearance uplift, applied multiplicatively */
    if ARREARS_BUCKET = '1-29'  then PD_12M = min(PD_12M * 1.35, 1);
    else if ARREARS_BUCKET = '30-59' then PD_12M = min(PD_12M * 2.60, 1);
    else if ARREARS_BUCKET = '60-89' then PD_12M = min(PD_12M * 4.10, 1);
    if FORBEARANCE_FL then PD_12M = min(PD_12M * 1.50, 1);
    if DEFAULT_FL then PD_12M = 1;
  run;
%mend;
