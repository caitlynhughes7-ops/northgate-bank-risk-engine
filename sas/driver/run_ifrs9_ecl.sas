/*--------------------------------------------------------------------------
  run_ifrs9_ecl.sas
  Main ECL orchestration. Invoked by run_month_end.sas.
  Usage:  sas -sysparm "202409 prod" driver/run_ifrs9_ecl.sas
--------------------------------------------------------------------------*/
%let PERIOD = %scan(&sysparm,1,%str( ));
%period_dates(&PERIOD);

%load_loan_tape(period=&PERIOD);
%clean_loan_tape();
%map_product_hierarchy();
%derive_arrears();

%ead_ccf(inds=stg.tape_arrears, outds=stg.ead);

/* PD - note pd_ttc is no longer invoked, see CHANGELOG v4.2 */
%pd_pit(inds=stg.ead, outds=stg.pd_pit);
%pd_term_structure(inds=stg.pd_pit, outds=stg.pd_curve);

/* LGD - secured and unsecured legs are built separately then stacked */
%lgd_secured(inds=stg.pd_pit, outds=stg.lgd_sec);
%lgd_unsecured(inds=stg.pd_pit, outds=stg.lgd_unsec);

data stg.lgd_all;
  set stg.lgd_sec(keep=ACCOUNT_ID SEGMENT EAD LGD PD_LIFETIME_ORIG DPD_N
                       FORBEARANCE_FL WATCHLIST_FL DEFAULT_FL EIR)
      stg.lgd_unsec(keep=ACCOUNT_ID SEGMENT EAD LGD PD_LIFETIME_ORIG DPD_N
                         FORBEARANCE_FL WATCHLIST_FL DEFAULT_FL EIR);
run;

proc sql;
  create table stg.lgd_life as
  select a.*, l.PD_LIFETIME
  from stg.lgd_all as a
  left join stg.pd_lifetime as l on a.ACCOUNT_ID = l.ACCOUNT_ID;
quit;

%staging_sicr(inds=stg.lgd_life, outds=stg.staged);
%fli_overlay(inds=stg.staged, outds=stg.exposure);

%discount_eir(inds=stg.pd_curve, outds=stg.disc);
%ecl_calc(curveds=stg.disc, expds=stg.exposure, outds=stg.ecl_acct);

%aggregate_reporting(inds=stg.ecl_acct, outds=out.ecl_by_segment);
%export_disclosure(inds=out.ecl_by_segment, period=&PERIOD);
%recon_controls();

%put NOTE: [ECL] run complete for &PERIOD;
