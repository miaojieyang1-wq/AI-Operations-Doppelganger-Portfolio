# 公式分段（可独立检索解释）

所属章节：六、目标泛函

## 六、目标泛函

对任一完整路径 a = (a₁,…,a_K)：

$$
\boxed{J(\mathbf{a}) = \sum_{k=1}^{K} d_k \;-\; \lambda_E \sum_{u \in \mathcal{C}} \max\!\big(0,\; \alpha e_u^{\max} - e_u^{\text{end}}\big) \;-\; \lambda_{SP} \max\!\big(0,\; 1 - SP^{\text{end}}\big)}
$$

其中 d_k 为第 k 步伤害期望由伤害外挂返回，角色集合 C 为独立注册表不从行动队列反推，α 取0.2为能量安全阈值比例，λ_E 和 λ_SP 为可调惩罚权重。
