# 公式分段（可独立检索解释）

所属章节：三、模块写入权隔离

## 三、模块写入权隔离

$$
\begin{aligned}
\Phi_{\text{Axis}}&: Q \mapsto Q' &&\text{仅写 } Q \\
\Phi_{\text{Toughness}}&: \mathbf{T} \mapsto \mathbf{T}' &&\text{仅写 } \mathbf{T} \\
\Phi_{\text{Buff}}&: B \mapsto B' &&\text{仅写 } B \\
\Phi_{\text{Energy}}&: \mathbf{E} \mapsto \mathbf{E}' &&\text{仅写 } \mathbf{E} \\
\Phi_{\text{SP}}&: SP \mapsto SP' &&\text{仅写 } SP \\
\Phi_{\text{Hit}}&: \text{生成分支方案} &&\text{无状态写入} \\
\Phi_{\text{DOT}}&: \mathbf{DOT} \mapsto \mathbf{DOT}',\;\mathbf{D} \mapsto \mathbf{D}' &&\text{仅写 } \mathbf{DOT},\mathbf{D}
\end{aligned}
$$
