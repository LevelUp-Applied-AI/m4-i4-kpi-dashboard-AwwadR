# KPI Framework — Amman Digital Market

In This analysis, I chose 5 KPIs to help us understand the the prformance of the market clearly.
I tried choosing indicators that covers more than one side Like: Time, Cities, Product Categories and Customers.

---

## KPI 1

- **Name:** Monthly Revenue
- **Definition:** This indicator explains the total revenue for each monthe from only the valid orders.
- **Formula:** Sum of `quantity × unit_price` grouped by `order_month`
- **Data Source (tables/columns):**
  - `orders["order_date"]`
  - `order_items["quantity"]`
  - `products["unit_price"]`
  - by excluding `orders["status"] = cancelled`
  - by excluding `order_items["quantity"] > 100`
- **Baseline Value:** Total revenue after cleaning the data was: **48,701.50**
- **Interpretation:** This KPI helps us show how the sales moved from month to month, and if there are months that stronger than others or not.
---

## KPI 2

- **Name:** Monthly Order Volume
- **Definition:** This indicator explains the number of valid orders for each month.
- **Formula:** Count of unique `order_id` grouped by `order_month`
- **Data Source (tables/columns):**
  - `orders["order_id"]`
  - `orders["order_date"]`
  - `orders["status"]`
- **Baseline Value:** The number of valid orders after cleaning was: **443 valid orders**
- **Interpretation:** This KPI is important for clarifying the makrket demand over time. And we can compare it with the revenue to understand if the increasing came from the higher number of orders or from higher order value.

---

## KPI 3

- **Name:** Revenue by City
- **Definition:** This indicator explains the total revenue from each city.
- **Formula:** Sum of `quantity × unit_price` grouped by `city`
- **Data Source (tables/columns):**
  - `customers["city"]`
  - `customers["customer_id"]`
  - `orders["customer_id"]`
  - `order_items["quantity"]`
  - `products["unit_price"]`
- **Baseline Value:** The top city in revenue was **Amman**
- **Interpretation:** This KPI helps us know which enhance the most revenue, so we can decide where to fucos marketing or customes follow-up.

---

## KPI 4

- **Name:** Average Order Value by Product Category
- **Definition:** This indicator explains the average order value inside each product category. 
- **Formula:** Average order value for each `category`, but first I calculated the sum of `quantity × unit_price` for each `order_id` and `category`, then took the average.
- **Data Source (tables/columns):**
  - `products["category"]`
  - `products["unit_price"]`
  - `order_items["quantity"]`
  - `order_items["order_id"]`
- **Baseline Value:** The category with the highest average order value was **Books** at about **70**
- **Interpretation:** This KPI helps us see which categories create higher value orders, and this is uesful for promotions or giving more attention to certain categories. 

**Statistical Validation**
- **H₀:** There is no difference in average order value between categories
- **H₁:** There is a difference in average order value in at least one category
- **Test Used:** One-way ANOVA
- **Why Appropriate:** Because we are comparing the averages of more than two categories, not just two groups
- **Test Statistic:** **56.7853**
- **p-value:** **2.1069868717112423e-52**
- **Effect Size:** **Eta squared = 0.2111**
- **Interpretation:** We reject H₀, which means average order value really does differ across categories and the difference is not random.

---

## KPI 5

- **Name:** Revenue by Registration Cohort
- **Definition:** This indicator shows the revenue based on the month customers registered.
- **Formula:** Sum of `quantity × unit_price` grouped by `registration_month`
- **Data Source (tables/columns):**
  - `customers["registration_date"]`
  - `customers["customer_id"]`
  - `orders["customer_id"]`
  - `order_items["quantity"]`
  - `products["unit_price"]`
- **Baseline Value:** Revenue was different across registration groups, that means some cohorts performed better than others.
- **Interpretation:** This KPI helps us understand if customers who signed up in certain periods were more valuable to the market or not.

---

## Additional Statistical Test

### Revenue Difference Between Top Two Cities
- **Related KPI:** Revenue by City
- **H₀:** There is no significant revenue difference between the top two cities
- **H₁:** There is a significant revenue difference between the top two cities
- **Test Used:** Independent samples t-test
- **Groups Compared:** **Amman** and **Irbid**
- **Test Statistic:** **-0.1201**
- **p-value:** **0.9053**
- **Effect Size:** **Cohen's d = -0.0378**
- **Interpretation:** We failed to reject H₀ that means the revenue difference between the top two cities wasn't statistically significant in this sample.

### City and Product Category Association
- **Related KPI:** Revenue by City / purchasing behavior by city
- **H₀:** There is no relationship between city and product category
- **H₁:** There is a relationship between city and product category
- **Test Used:** Chi-square test of independence
- **Test Statistic:** **20.6990**
- **p-value:** **0.8971**
- **Effect Size:** **Cramer's V = 0.0619**
- **Interpretation:** We failed to reject H₀, that means the data doesn't show a clear relationship between the customer city and the product category they buy from.