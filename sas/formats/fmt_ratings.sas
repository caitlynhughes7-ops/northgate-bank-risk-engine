proc format;
  /* internal masterscale - do not amend without Model Governance approval */
  value grade
    1 = 'AAA/AA'  2 = 'A'    3 = 'BBB+'  4 = 'BBB'  5 = 'BBB-'
    6 = 'BB+'     7 = 'BB'   8 = 'BB-'   9 = 'B+'  10 = 'B'
   11 = 'B-'     12 = 'CCC' 13 = 'CC'   14 = 'C'  15 = 'D';
run;
