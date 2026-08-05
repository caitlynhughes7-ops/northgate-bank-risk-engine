/*--------------------------------------------------------------------------
  m_rpt_gl_feed_recon.sas
  Finance GL feed reconciliation
  Output: &OUTBOUND./gl_feed_recon_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro rpt_gl_feed_recon(inds=stg.ecl_acct, period=);
  %log_step(rpt_gl_feed_recon);

  proc sql;
    create table stg.rpt_gl_feed_recon as
    select SEGMENT, SICR_REASON,
           count(*)  as N_EXPOSURES,
           sum(EAD)  as EAD  format=comma18.2,
           sum(ECL)  as ECL  format=comma18.2,
           mean(PD_LIFETIME) as AVG_PD_LIFETIME format=percent9.4
    from &inds
    where DEFAULT_FL = 1
    group by SEGMENT, SICR_REASON
    order by SEGMENT, SICR_REASON;
  quit;

  proc export data=stg.rpt_gl_feed_recon
       outfile="&OUTBOUND./gl_feed_recon_&period..csv"
       dbms=csv replace;
  run;
%mend;

%macro rpt_gl_feed_recon_validate(period=);
  /* control totals circulated with the submission - do not remove, these are
     referenced in the Regulatory Reporting control attestation                          */
  %local n_null n_neg tot;
  proc sql noprint;
    select count(*) into :n_null from stg.rpt_gl_feed_recon where EAD is null;
    select count(*) into :n_neg  from stg.rpt_gl_feed_recon where ECL < 0;
    select sum(ECL) into :tot    from stg.rpt_gl_feed_recon;
  quit;

  %if &n_null > 0 %then %put ERROR: [gl_feed_recon] &n_null rows with null EAD;
  %if &n_neg  > 0 %then %put ERROR: [gl_feed_recon] &n_neg rows with negative ECL;
  %put NOTE: [gl_feed_recon] submission total ECL &tot;

  /* prior period comparison - variance over 10% is queried by Regulatory Reporting */
  proc sql;
    create table stg.rpt_gl_feed_recon_var as
    select c.*, p.ECL as ECL_PRIOR,
           case when p.ECL > 0 then (c.ECL - p.ECL) / p.ECL else . end
             as VAR_PCT format=percent9.2
    from stg.rpt_gl_feed_recon as c
    left join hist.rpt_gl_feed_recon_&PRIOR_YYYYMM as p
      on c.SEGMENT = p.SEGMENT and c.STAGE = p.STAGE;
  quit;

  data _null_;
    set stg.rpt_gl_feed_recon_var;
    if not missing(VAR_PCT) and abs(VAR_PCT) > 0.10 then
      put "WARNING: [gl_feed_recon] variance " VAR_PCT percent9.2 " exceeds tolerance";
  run;
%mend;

%macro rpt_gl_feed_recon_archive(period=);
  /* retained for 10 years per the group records retention schedule */
  data hist.rpt_gl_feed_recon_&period.;
    set stg.rpt_gl_feed_recon;
    RUN_DTTM = datetime();
    RUN_ENV  = "&ENV";
    format RUN_DTTM datetime20.;
  run;

  proc datasets library=stg nolist;
    delete rpt_gl_feed_recon_var;
  quit;
%mend;
