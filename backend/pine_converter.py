import re

class PineConverter:
    def convert(self, pine_code: str) -> str:
        # Pre-process: Join continuation lines
        # We must preserve indentation of the START of the line, but stripped content for logic.
        raw_lines = pine_code.split('\n')
        joined_lines = []
        
        for rline in raw_lines:
            content = rline.strip()
            if not content or content.startswith("//"):
                continue
            
            # Check for continuation - enhanced to handle function calls and operators
            if joined_lines:
                last_stripped = joined_lines[-1].strip()
                # Continue if: starts with operator, starts with quote, previous ends with operator,
                # OR previous line ends with open paren/comma (function call continuation)
                if (content.startswith("+") or 
                    content.startswith("'") or 
                    content.startswith('"') or 
                    last_stripped.endswith("+") or
                    last_stripped.endswith(",") or
                    last_stripped.endswith("(")):
                    joined_lines[-1] += " " + content
                    continue
            
            joined_lines.append(rline) # Keep original indentation
        
        py_lines = [
            "import pandas as pd",
            # "import pandas_ta as ta",
            "import numpy as np",
            "",
            "def strategy(df):",
            "    # Standardize columns",
            "    close = df['close']",
            "    open_ = df['open']",
            "    high = df['high']",
            "    low = df['low']",
            "    volume = df['volume']",
            "    time = df['time']",
            "",
            "    # Signal columns",
            "    df['long_entry'] = False",
            "    df['short_entry'] = False",
            "    df['long_exit'] = False",
            "    df['short_exit'] = False",
            "    ",
            "    # Pine constants",
            "    na = np.nan",
            "    true = True",
            "    false = False",
            ""
        ]

        base_indent = "    "
        current_indent_level = 0  # Track indentation for nested blocks
        last_was_control_flow = False  # Track if last line was if/elif/else/for/while
        
        for i, line in enumerate(joined_lines):
            # Separating indent and content
            indent_str = line[:len(line) - len(line.lstrip())]
            content = line.strip()
            
            # Calculate indent level from the original Pine Script
            pine_indent_level = len(indent_str) // 4  # Assuming 4 spaces per indent
            
            # 1. Regex replacements
            content = re.sub(r"str\.tostring\(([^)]+)\)", r"str(\1)", content)
            content = content.replace("syminfo.ticker", '"SYMBOL"')
            content = re.sub(r"str\((time),\s*\"[^\"]+\"\)", r"str(\1)", content)

            # Array indexing
            for v in ["open", "high", "low", "close", "volume", "time"]:
                tgt = f"{v}_" if v == "open" else v
                pattern = f"\\b{v}\\s*\\[\\s*(\\d+)\\s*\\]"
                content = re.sub(pattern, f"{tgt}.shift(\\1)", content)

            # Mutable assignment
            content = content.replace(":=", "=")
            
            # Variable declarations
            if content.startswith("var "):
                content = content[4:].strip()
            
            for type_kw in ["int", "float", "bool", "color", "string"]:
                if content.startswith(f"{type_kw} "):
                    content = content[len(type_kw)+1:].strip()

            # -----------------------------------------------
            # Logic Handlers (Order matters!)
            
            # Check if we need to add 'pass' for empty control flow blocks
            # Look ahead to see if next line is dedented or is another control flow
            if last_was_control_flow:
                next_line_content = ""
                next_indent_level = 0
                if i + 1 < len(joined_lines):
                    next_line = joined_lines[i + 1]
                    next_indent_str = next_line[:len(next_line) - len(next_line.lstrip())]
                    next_indent_level = len(next_indent_str) // 4
                    next_line_content = next_line.strip()
                
                # If next line is dedented or at same level, or is a comment, we need pass
                if (next_indent_level <= current_indent_level or 
                    not next_line_content or 
                    next_line_content.startswith("//") or
                    next_line_content.startswith("alert(") or
                    "alert(" in next_line_content):
                    py_lines.append(f"{base_indent}{'    ' * (current_indent_level + 1)}pass")
                
                last_was_control_flow = False
            
            # Orphaned line check (heuristic)
            if "=" in content and "," in content and content.endswith(")"):
                 if not (content.startswith("strategy") or content.startswith("plot") or content.startswith("alert")):
                      # Likely orphaned args or unknown function continuation
                      py_lines.append(f"{base_indent}{'    ' * pine_indent_level}#{content}")
                      continue

            # Plot/Shape/etc -> Ignore
            if content.startswith("plot") or content.startswith("bgcolor") or content.startswith("fill"):
                 py_lines.append(f"{base_indent}{'    ' * pine_indent_level}#{content}")
                 continue

            # Indicator -> Ignore
            if content.startswith("indicator"):
                 py_lines.append(f"{base_indent}{'    ' * pine_indent_level}#{content}")
                 continue

            # Strategy calls
            if content.startswith("strategy.entry"):
                if "strategy.long" in content and "when=" in content:
                    cond = content.split("when=")[1].replace(")", "").strip()
                    py_lines.append(f"{base_indent}{'    ' * pine_indent_level}df.loc[{cond}, 'long_entry'] = True")
                    
                elif "strategy.short" in content and "when=" in content:
                    cond = content.split("when=")[1].replace(")", "").strip()
                    py_lines.append(f"{base_indent}{'    ' * pine_indent_level}df.loc[{cond}, 'short_entry'] = True")

            elif content.startswith("strategy.close"):
                 if "when=" in content:
                    cond = content.split("when=")[1].replace(")", "").strip()
                    if "Long" in content:
                         py_lines.append(f"{base_indent}{'    ' * pine_indent_level}df.loc[{cond}, 'long_exit'] = True")
                    elif "Short" in content:
                         py_lines.append(f"{base_indent}{'    ' * pine_indent_level}df.loc[{cond}, 'short_exit'] = True")

            # Control Flow (if) - Must be before '=' check!
            elif content.startswith("if "):
                 # Extract condition
                 condition = content[3:].strip()
                 # Ensure colon at the end
                 if not condition.endswith(":"):
                      condition += ":"
                 py_lines.append(f"{base_indent}{'    ' * pine_indent_level}if {condition}")
                 current_indent_level = pine_indent_level
                 last_was_control_flow = True

            # Variable assignment (only if '=' is present and it's NOT a comparison '==', '!=', '>=', '<=')
            elif "=" in content:
                # Check if it's likely a comparison or assignment
                parts = content.split("=")
                var_check = parts[0].strip()
                
                # Check for comparison operators
                if content.find("==") != -1:
                     first_eq = content.find("=")
                     if content[first_eq:first_eq+2] == "==":
                          # It's an expression statement
                          py_lines.append(f"{base_indent}{'    ' * pine_indent_level}{content}")
                          continue
                
                # It is likely an assignment "x = ..."
                var_name = var_check
                expr = content.split("=", 1)[1].strip()

                # Handle TA functions in expression
                if "ta.sma" in expr:
                    m = re.search(r"ta\.sma\(([^,]+),\s*([^)]+)\)", expr)
                    if m:
                        src, length = m.groups()
                        py_expr = f"{src}.rolling({length}).mean()"
                        py_lines.append(f"{base_indent}{'    ' * pine_indent_level}{var_name} = {py_expr}")
                        continue

                if "ta.ema" in expr:
                    m = re.search(r"ta\.ema\(([^,]+),\s*([^)]+)\)", expr)
                    if m:
                        src, length = m.groups()
                        py_expr = f"{src}.ewm(span={length}, adjust=False).mean()"
                        py_lines.append(f"{base_indent}{'    ' * pine_indent_level}{var_name} = {py_expr}")
                        continue
                
                if "ta.rsi" in expr:
                     m = re.search(r"ta\.rsi\(([^,]+),\s*([^)]+)\)", expr)
                     if m:
                        src, length = m.groups()
                        py_lines.append(f"{base_indent}{'    ' * pine_indent_level}# RSI {length}")
                        py_lines.append(f"{base_indent}{'    ' * pine_indent_level}delta_{var_name} = {src}.diff()")
                        py_lines.append(f"{base_indent}{'    ' * pine_indent_level}gain_{var_name} = (delta_{var_name}.where(delta_{var_name} > 0, 0)).rolling({length}).mean()")
                        py_lines.append(f"{base_indent}{'    ' * pine_indent_level}loss_{var_name} = (-delta_{var_name}.where(delta_{var_name} < 0, 0)).rolling({length}).mean()")
                        py_lines.append(f"{base_indent}{'    ' * pine_indent_level}rs_{var_name} = gain_{var_name} / loss_{var_name}")
                        py_lines.append(f"{base_indent}{'    ' * pine_indent_level}{var_name} = 100 - (100 / (1 + rs_{var_name}))")
                        continue

                # Default assignment
                py_lines.append(f"{base_indent}{'    ' * pine_indent_level}{var_name} = {expr}")

            # Alert - comment out as it's not supported in backtesting
            elif content.startswith("alert(") or "alert(" in content:
                 # Comment out the entire alert call
                 py_lines.append(f"{base_indent}{'    ' * pine_indent_level}# {content}")
            
            else:
                 # Unknown / bare expression
                 py_lines.append(f"{base_indent}{'    ' * pine_indent_level}{content}")

        py_lines.append(f"{base_indent}return df")
        
        return "\n".join(py_lines)

    def _convert_crossovers(self, expr):
        # Handle ta.crossover(a, b) -> ((a > b) & (a.shift(1) < b.shift(1)))
        # This needs to be done on the expression string before assignment
        if "ta.crossover" in expr:
             # Basic regex for replacing ta.crossover(x, y)
             # Note: nested calls not supported well with regex
             expr = re.sub(r"ta\.crossover\(([^,]+),\s*([^)]+)\)", 
                           r"((\1 > \2) & (\1.shift(1) < \2.shift(1)))", expr)
        if "ta.crossunder" in expr:
             expr = re.sub(r"ta\.crossunder\(([^,]+),\s*([^)]+)\)", 
                           r"((\1 < \2) & (\1.shift(1) > \2.shift(1)))", expr)
        return expr
