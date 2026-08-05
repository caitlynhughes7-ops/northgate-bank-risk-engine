/*--------------------------------------------------------------------------
  autoexec.sas   Northgate Bank Group - IFRS 9 ECL Engine
  Sets up libraries, macro autocall path and environment configuration.
  MUST be invoked from the sas/ directory (see docs/ops/RUNBOOK.md).
--------------------------------------------------------------------------*/
options nomprint nosymbolgen nomlogic;
options compress=yes msglevel=i;

%let ROOT = %sysfunc(pathname(work));
%let BASE = ..;

%macro _env(e);
  %if %length(&e)=0 %then %let e=uat;
  %include "&BASE./config/env/&e..cfg";
%mend;

/* environment is passed by the shell wrapper as SYSPARM2 */
%_env(%scan(&sysparm,2,%str( )));

libname raw     "&INBOUND" access=readonly;
libname stg     "&ROOT";
libname out     "&OUTBOUND";
libname hist    "&HISTLIB";

options sasautos=("&BASE./sas/macros" sasautos);

%include "&BASE./sas/formats/fmt_product.sas";
%include "&BASE./sas/formats/fmt_ratings.sas";

%put NOTE: ECL engine initialised for environment &ENV;
