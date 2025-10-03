Judging
Severity is measured by the finding’s impact on the entire Ethereum network.
The network impact for each client can be found in the Scope/Clients section below.
The Ethereum Foundation’s Protocol Security team will assist in judging the findings and have the final word on all judging related decisions.
A finding may, if deemed relevant by the judges, have its severity upgraded from the severity definitions in the next section (for example Medium to High).
Unrelated findings cannot be chained together and are treated individually.
All submissions (except informational) must include an executable coded proof of concept at the time of submission.
Severity Definitions
Critical Severity
Vulnerabilities that allow an attacker to slash more than 50% of validators, exploit an EIP/specification or client bug to easily create an infinite amount of ETH which is finalized by the network, steal ETH from all EOAs, burn ETH from all EOAs, or take down the entire network by sending a single malicious on-chain transaction that ends up crashing all clients.

High Severity
Vulnerabilities that allow an attacker to slash more than 33% of validators, trivially cause network splits affecting more than 33% of the network, or being able to bring down more than 33% of the network by sending a single network packet or an on-chain transaction.

Medium Severity
Vulnerabilities that allow an attacker to slash more than 1% of validators, trivially cause network splits affecting more than 5% of the network, or being able to bring down more than 5% of the network by sending a single network packet or an on-chain transaction.

Low Severity
Vulnerabilities that allow an attacker to slash more than 0.01% of validators, trivially cause network splits affecting at least 0.01% of the network, or being able to bring down more than 0.01% of the network by sending a single network packet or an on-chain transaction.

Informational Severity
Observations or recommendations regarding code quality, maintainability, or system architecture that do not present a direct security risk. These findings aim to provide insights for potential improvements rather than addressing an immediate vulnerability. Only applicable if the team decides to implement a change based on the report.

Informational issues are valid if they don't lead to a sufficient impact to count as Low or higher and are valuable enough for the client that they decided to implement the change in the code. Issues related to parts under the "Out of scope" section will not be considered valid. Informational issues won't have duplicates, and only the first one is valid. They also don't qualify for the 1st and 2nd week multipliers, as they apply only to issues in the main pot.

Scope
Only Fusaka-specific code is in scope of this competition. Any vulnerabilities that are not specifically related to the upgrade are out of scope of the competition and should instead be submitted via the Ethereum Foundation’s Bug Bounty Program. Items scheduled for future upgrades are not in scope. In the case where there is already an EIP that would mitigate an attack, or any type of public post such as a PR, commit, blog posts, public discord messages, etc., the issue is considered a “known issue” and is not eligible.

Out of scope
Typographical errors.
Tests, scripts and other code or documentation that can not be exploited when the client is running
Anything that can not be exploited on a live network.
Vulnerabilities not specific to Fusaka.
High-effort (sustained, CPU or bandwidth intensive, and/or requires more than 1 packet or on-chain transaction) single-peer DoS attacks.
All “TODO”/“FIXME”/“BUG”/“HACK” and similar items referenced in any of the codebases are considered known issues.
Any publicly known issues (includes forum posts, PRs, github issues, commits, blog posts, public discord messages, etc.)