* ==============================================================================
* Clean Workforce & R&D Backtest (Works for both 20-Stock and 40-Stock CSVs)
* ==============================================================================
clear all
cls
set more off
cd "C:\Users\fares\Documents\CFA_Workforce_Backtest"
import delimited "workforce_panel.csv", clear

encode ticker, gen(id)
gen ym = ym(year, month)
format ym %tm
xtset id ym

bysort id (ym): gen ex_ret_lead1 = ret[_n+1] - rf[_n+1]

* 1. Peer Sector Groups & Uncorrupted YoY Signals
gen sector_grp = 1 if inlist(gics_ind, "Tech_Hardware", "Semiconductors")
replace sector_grp = 2 if inlist(gics_ind, "Software", "IT_Services")
replace sector_grp = 3 if inlist(gics_ind, "Internet_Retail", "Interactive_Media")
replace sector_grp = 4 if gics_ind == "Biotech"
replace sector_grp = 5 if gics_ind == "Machinery"

gen true_rd = raw_st * employees
bysort id (ym): gen rd_yoy  = (true_rd - true_rd[_n-12]) / (true_rd[_n-12] + 0.001)
bysort id (ym): gen emp_yoy = (employees - employees[_n-12]) / employees[_n-12] if employees != 25000 & employees[_n-12] != 25000
bysort id (ym): gen rgr_yoy = (raw_rgr - raw_rgr[_n-12]) / (raw_rgr[_n-12] + 0.001)
gen skill_acc = cond(!missing(emp_yoy), rd_yoy - 0.5 * emp_yoy, rd_yoy)

foreach var in rd_yoy skill_acc rgr_yoy {
    bysort sector_grp ym: egen mean_`var' = mean(`var')
    bysort sector_grp ym: egen sd_`var'   = sd(`var')
    gen z_`var' = cond(sd_`var' > 0 & !missing(sd_`var'), (`var' - mean_`var') / sd_`var', 0)
    replace z_`var' = clip(z_`var', -3, 3) if !missing(z_`var')
}

* 2. Composite Score & Tercile Assignment
gen clean_score = 0.45 * z_skill_acc + 0.35 * z_rd_yoy + 0.20 * z_rgr_yoy
drop if missing(clean_score, ex_ret_lead1)
bysort ym (clean_score): gen port = ceil(3 * _n / _N)
bysort ym: egen univ_bench = mean(ex_ret_lead1)

* 3. Firm-Month Panel Regression (Before Collapse)
gen firm_active = ex_ret_lead1 - univ_bench
newey firm_active mktrf smb hml rmw cma if port == 2, lag(3) force

* 4. Monthly Portfolio Collapse & Regressions
collapse (mean) port_ret = ex_ret_lead1 (first) univ_bench mktrf smb hml rmw cma rf, by(ym port)
reshape wide port_ret, i(ym) j(port)
tsset ym

gen ls_linear    = port_ret3 - port_ret1
gen mid_active   = port_ret2 - univ_bench
gen mid_vs_tails = port_ret2 - 0.5 * (port_ret1 + port_ret3)

newey ls_linear mktrf smb hml rmw cma, lag(3)
newey mid_active mktrf smb hml rmw cma, lag(3)
newey mid_vs_tails mktrf smb hml rmw cma, lag(3)

* 5. Cumulative Wealth Plot ($100k Initial)
foreach p in top mid bot univ {
    gen w_`p' = 100
}
replace w_top  = w_top[_n-1]  * (1 + port_ret3 + rf)  if _n > 1
replace w_mid  = w_mid[_n-1]  * (1 + port_ret2 + rf)  if _n > 1
replace w_bot  = w_bot[_n-1]  * (1 + port_ret1 + rf)  if _n > 1
replace w_univ = w_univ[_n-1] * (1 + univ_bench + rf) if _n > 1

tsline w_mid w_univ w_top w_bot, ///
    title("Non-Linear Workforce & R&D Scaling (USD 100k Initial)") ///
    ytitle("Portfolio Value (USD k)") xtitle("Date") ///
    legend(label(1 "Middle Tercile: Disciplined Scaling") ///
           label(2 "Equal-Weight Benchmark") ///
           label(3 "Top Tercile: Aggressive Expansion") ///
           label(4 "Bottom Tercile: Stagnation / Cuts")) ///
    lwidth(thick medthick medium medium)
graph export "nonlinear_workforce_backtest.png", replace width(2400)