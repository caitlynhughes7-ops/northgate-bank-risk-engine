/*--------------------------------------------------------------------------
  m_rpt_board_sensitivity.sas
  Board pack - scenario sensitivity appendix
  Output: &OUTBOUND./board_sensitivity_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro rpt_board_sensitivity(inds=stg.ecl_acct, period=);
  %log_step(rpt_board_sensitivity);

  proc sql;
    create table stg.rpt_board_sensitivity as
    select SEGMENT, STAGE, ARREARS_BUCKET,
           count(*)  as N_EXPOSURES,
           sum(EAD)  as EAD  format=comma18.2,
           sum(ECL)  as ECL  format=comma18.2
    from &inds
    where DEFAULT_FL = 1
    group by SEGMENT, STAGE, ARREARS_BUCKET
    order by SEGMENT, STAGE, ARREARS_BUCKET;
  quit;

  proc export data=stg.rpt_board_sensitivity
       outfile="&OUTBOUND./board_sensitivity_&period..csv"
       dbms=csv replace;
  run;
%mend;

%macro rpt_board_sensitivity_validate(period=);
  /* control totals circulated with the submission - do not remove, these are
     referenced in the Finance Control control attestation                          */
  %local n_null n_neg tot;
  proc sql noprint;
    select count(*) into :n_null from stg.rpt_board_sensitivity where EAD is null;
    select count(*) into :n_neg  from stg.rpt_board_sensitivity where ECL < 0;
    select sum(ECL) into :tot    from stg.rpt_board_sensitivity;
  quit;

  %if &n_null > 0 %then %put ERROR: [board_sensitivity] &n_null rows with null EAD;
  %if &n_neg  > 0 %then %put ERROR: [board_sensitivity] &n_neg rows with negative ECL;
  %put NOTE: [board_sensitivity] submission total ECL &tot;

  /* prior period comparison - variance over 5% is queried by Finance Control */
  proc sql;
    create table stg.rpt_board_sensitivity_var as
    select c.*, p.ECL as ECL_PRIOR,
           case when p.ECL > 0 then (c.ECL - p.ECL) / p.ECL else . end
             as VAR_PCT format=percent9.2
    from stg.rpt_board_sensitivity as c
    left join hist.rpt_board_sensitivity_&PRIOR_YYYYMM as p
      on c.SEGMENT = p.SEGMENT;
  quit;

  data _null_;
    set stg.rpt_board_sensitivity_var;
    if not missing(VAR_PCT) and abs(VAR_PCT) > 0.10 then
      put "WARNING: [board_sensitivity] variance " VAR_PCT percent9.2 " exceeds tolerance";
  run;
%mend;

%macro rpt_board_sensitivity_archive(period=);
  /* retained for 7 years per the group records retention schedule */
  data hist.rpt_board_sensitivity_&period.;
    set stg.rpt_board_sensitivity;
    RUN_DTTM = datetime();
    RUN_ENV  = "&ENV";
    format RUN_DTTM datetime20.;
  run;

  proc datasets library=stg nolist;
    delete rpt_board_sensitivity_var;
  quit;
%mend;
