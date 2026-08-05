/*--------------------------------------------------------------------------
  m_rpt_ifrs7_ecl_movement.sas
  IFRS 7 ECL movement (opening to closing)
  Output: &OUTBOUND./ifrs7_ecl_movement_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro rpt_ifrs7_ecl_movement(inds=stg.ecl_acct, period=);
  %log_step(rpt_ifrs7_ecl_movement);

  proc sql;
    create table stg.rpt_ifrs7_ecl_movement as
    select STAGE,
           count(*)  as N_EXPOSURES,
           sum(EAD)  as EAD  format=comma18.2,
           sum(ECL)  as ECL  format=comma18.2,
           sum(ECL)/sum(EAD) as COVERAGE format=percent9.4
    from &inds
    group by STAGE
    order by STAGE;
  quit;

  proc export data=stg.rpt_ifrs7_ecl_movement
       outfile="&OUTBOUND./ifrs7_ecl_movement_&period..csv"
       dbms=csv replace;
  run;
%mend;

%macro rpt_ifrs7_ecl_movement_validate(period=);
  /* control totals circulated with the submission - do not remove, these are
     referenced in the Finance Control control attestation                          */
  %local n_null n_neg tot;
  proc sql noprint;
    select count(*) into :n_null from stg.rpt_ifrs7_ecl_movement where EAD is null;
    select count(*) into :n_neg  from stg.rpt_ifrs7_ecl_movement where ECL < 0;
    select sum(ECL) into :tot    from stg.rpt_ifrs7_ecl_movement;
  quit;

  %if &n_null > 0 %then %put ERROR: [ifrs7_ecl_movement] &n_null rows with null EAD;
  %if &n_neg  > 0 %then %put ERROR: [ifrs7_ecl_movement] &n_neg rows with negative ECL;
  %put NOTE: [ifrs7_ecl_movement] submission total ECL &tot;

  /* prior period comparison - variance over 10% is queried by Finance Control */
  proc sql;
    create table stg.rpt_ifrs7_ecl_movement_var as
    select c.*, p.ECL as ECL_PRIOR,
           case when p.ECL > 0 then (c.ECL - p.ECL) / p.ECL else . end
             as VAR_PCT format=percent9.2
    from stg.rpt_ifrs7_ecl_movement as c
    left join hist.rpt_ifrs7_ecl_movement_&PRIOR_YYYYMM as p
      on c.SEGMENT = p.SEGMENT;
  quit;

  data _null_;
    set stg.rpt_ifrs7_ecl_movement_var;
    if not missing(VAR_PCT) and abs(VAR_PCT) > 0.10 then
      put "WARNING: [ifrs7_ecl_movement] variance " VAR_PCT percent9.2 " exceeds tolerance";
  run;
%mend;

%macro rpt_ifrs7_ecl_movement_archive(period=);
  /* retained for 6 years per the group records retention schedule */
  data hist.rpt_ifrs7_ecl_movement_&period.;
    set stg.rpt_ifrs7_ecl_movement;
    RUN_DTTM = datetime();
    RUN_ENV  = "&ENV";
    format RUN_DTTM datetime20.;
  run;

  proc datasets library=stg nolist;
    delete rpt_ifrs7_ecl_movement_var;
  quit;
%mend;
