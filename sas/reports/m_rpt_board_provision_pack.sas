/*--------------------------------------------------------------------------
  m_rpt_board_provision_pack.sas
  Board Risk Committee provision pack
  Output: &OUTBOUND./board_provision_pack_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro rpt_board_provision_pack(inds=stg.ecl_acct, period=);
  %log_step(rpt_board_provision_pack);

  proc sql;
    create table stg.rpt_board_provision_pack as
    select SEGMENT,
           count(*)  as N_EXPOSURES,
           sum(EAD)  as EAD  format=comma18.2,
           sum(ECL)  as ECL  format=comma18.2,
           mean(LGD) as AVG_LGD format=percent9.2
    from &inds
    group by SEGMENT
    order by SEGMENT;
  quit;

  proc export data=stg.rpt_board_provision_pack
       outfile="&OUTBOUND./board_provision_pack_&period..csv"
       dbms=csv replace;
  run;
%mend;

%macro rpt_board_provision_pack_validate(period=);
  /* control totals circulated with the submission - do not remove, these are
     referenced in the Regulatory Reporting control attestation                          */
  %local n_null n_neg tot;
  proc sql noprint;
    select count(*) into :n_null from stg.rpt_board_provision_pack where EAD is null;
    select count(*) into :n_neg  from stg.rpt_board_provision_pack where ECL < 0;
    select sum(ECL) into :tot    from stg.rpt_board_provision_pack;
  quit;

  %if &n_null > 0 %then %put ERROR: [board_provision_pack] &n_null rows with null EAD;
  %if &n_neg  > 0 %then %put ERROR: [board_provision_pack] &n_neg rows with negative ECL;
  %put NOTE: [board_provision_pack] submission total ECL &tot;

  /* prior period comparison - variance over 10% is queried by Regulatory Reporting */
  proc sql;
    create table stg.rpt_board_provision_pack_var as
    select c.*, p.ECL as ECL_PRIOR,
           case when p.ECL > 0 then (c.ECL - p.ECL) / p.ECL else . end
             as VAR_PCT format=percent9.2
    from stg.rpt_board_provision_pack as c
    left join hist.rpt_board_provision_pack_&PRIOR_YYYYMM as p
      on c.SEGMENT = p.SEGMENT and c.STAGE = p.STAGE;
  quit;

  data _null_;
    set stg.rpt_board_provision_pack_var;
    if not missing(VAR_PCT) and abs(VAR_PCT) > 0.15 then
      put "WARNING: [board_provision_pack] variance " VAR_PCT percent9.2 " exceeds tolerance";
  run;
%mend;

%macro rpt_board_provision_pack_archive(period=);
  /* retained for 6 years per the group records retention schedule */
  data hist.rpt_board_provision_pack_&period.;
    set stg.rpt_board_provision_pack;
    RUN_DTTM = datetime();
    RUN_ENV  = "&ENV";
    format RUN_DTTM datetime20.;
  run;

  proc datasets library=stg nolist;
    delete rpt_board_provision_pack_var;
  quit;
%mend;
