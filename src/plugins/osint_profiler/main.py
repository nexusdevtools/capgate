# src/plugins/osint_profiler/main.py
"""
OSINT Profiler Plugin: Gathers open-source intelligence and checks for leaked credentials.
"""

import os
import json
import time
from typing import Dict, Any, Optional, List, Callable

from base.logger import logger
from base.state_management.context import CapGateContext
from base.state_management.state import AppState
from paths import CAPGATE_DATA_DIR # Assuming CAPGATE_DATA_DIR is defined in paths.py

class OSINTProfiler:
    """
    Manages OSINT gathering, data breach checks, and target profiling.
    """
    def __init__(self, app_context: CapGateContext):
        self.app_context = app_context
        self.app_state: AppState = app_context.state
        self.logger = logger
        self.findings: List[Dict[str, Any]] = [] # To store all findings

        # CLI arguments will be pre-parsed and available in app_context
        self.target_email: Optional[str] = self.app_context.get("target_email")
        self.target_domain: Optional[str] = self.app_context.get("target_domain")
        self.target_username: Optional[str] = self.app_context.get("target_username")
        self.hibp_api_key: Optional[str] = self.app_context.get("pwned_api_key") or os.getenv("HIBP_API_KEY")
        self.profile_company_name: Optional[str] = self.app_context.get("profile_company")
        self.output_dir: str = self.app_context.get("output_dir", os.path.join(CAPGATE_DATA_DIR, "osint_profiler_output"))
        self.enrich_appstate: bool = self.app_context.get("enrich_appstate", False)
        self.generate_wordlist: bool = self.app_context.get("generate_wordlist", False)

        os.makedirs(self.output_dir, exist_ok=True)
        self.output_filepath = os.path.join(self.output_dir, f"osint_findings_{int(time.time())}.jsonl")

    def _check_breaches_hibp(self, email: Optional[str] = None, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Checks Have I Been Pwned for data breaches for a given email or domain.
        Note: Requires 'requests' library and HIBP API key for domain/range searches.
        For individual email hashes, it can be done via k-anonymity (Pwned Passwords API).
        For simplicity, we'll assume direct API call with key if provided.
        """
        self.logger.info(f"[OSINT] Checking HIBP for breaches (Email: {email}, Domain: {domain})...")
        found_breaches: List[Dict[str, Any]] = []
        
        # Placeholder for HIBP API interaction
        # In a real implementation, you'd use a library like `hibp-python` or `requests`
        # and handle API keys, rate limits, and different endpoints (breaches, pastes).
        
        if not self.hibp_api_key:
            self.logger.warning("[OSINT] HIBP API Key not provided. Cannot perform comprehensive data breach checks.")
            self.logger.warning("[OSINT] For HIBP API key, visit https://haveibeenpwned.com/API/Key")
            return []

        # Example (conceptual) HIBP API call structure:
        # headers = {"User-Agent": "CapGate-OSINT-Profiler", "hibp-api-key": self.hibp_api_key}
        # if email:
        #     try:
        #         response = requests.get(f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}", headers=headers, timeout=10)
        #         if response.status_code == 200:
        #             found_breaches.extend(response.json())
        #             self.logger.info(f"[OSINT] Found {len(response.json())} breaches for email: {email}")
        #         elif response.status_code == 404:
        #             self.logger.info(f"[OSINT] No breaches found for email: {email}")
        #         else:
        #             self.logger.error(f"[OSINT] HIBP API error for email {email}: {response.status_code} - {response.text}")
        #     except Exception as e:
        #         self.logger.error(f"[OSINT] Error querying HIBP for email {email}: {e}")
        # if domain:
        #     try:
        #         response = requests.get(f"https://haveibeenpwned.com/api/v3/breaches?domain={domain}", headers=headers, timeout=10)
        #         if response.status_code == 200:
        #             found_breaches.extend(response.json())
        #             self.logger.info(f"[OSINT] Found {len(response.json())} breaches for domain: {domain}")
        #         elif response.status_code == 404:
        #             self.logger.info(f"[OSINT] No breaches found for domain: {domain}")
        #         else:
        #             self.logger.error(f"[OSINT] HIBP API error for domain {domain}: {response.status_code} - {response.text}")
        #     except Exception as e:
        #         self.logger.error(f"[OSINT] Error querying HIBP for domain {domain}: {e}")

        # Simulate findings for demonstration
        if email and "test@example.com" in email:
            found_breaches.append({"Source": "Simulated HIBP", "Email": email, "BreachName": "ExampleCorp Leak", "Date": "2023-01-15", "DataClasses": ["Email addresses", "Passwords"]})
        if domain and "example.com" in domain:
            found_breaches.append({"Source": "Simulated HIBP", "Domain": domain, "BreachName": "GenericForum Hack", "Date": "2022-11-01", "DataClasses": ["Usernames", "Passwords"]})

        return found_breaches

    def _profile_target_osint(self, company_name: Optional[str] = None, username: Optional[str] = None) -> Dict[str, Any]:
        """
        Performs general OSINT gathering to build a target profile.
        This is a conceptual placeholder for more advanced OSINT tools.
        """
        self.logger.info(f"[OSINT] Profiling target (Company: {company_name}, Username: {username})...")
        profile_data: Dict[str, Any] = {}

        if company_name:
            self.logger.info(f"[OSINT] Simulating OSINT gathering for company: {company_name}")
            profile_data["company_name"] = company_name
            profile_data["known_employees"] = ["john.doe@example.com", "jane.smith@example.com"]
            profile_data["common_passwords_patterns"] = ["Summer2023!", f"{company_name.lower()}123", "Password1"]
            profile_data["public_ip_ranges"] = ["192.0.2.0/24", "203.0.113.0/24"] # Example public IP ranges
            self.findings.append({"type": "company_profile", "data": profile_data})

        if username:
            self.logger.info(f"[OSINT] Simulating OSINT gathering for username: {username}")
            profile_data["username"] = username
            profile_data["associated_emails"] = [f"{username}@mail.com"]
            profile_data["potential_social_media"] = [f"linkedin.com/in/{username}"]
            self.findings.append({"type": "username_profile", "data": profile_data})

        return profile_data

    def _generate_ai_ml_wordlist(self, profile_data: Dict[str, Any]) -> Optional[str]:
        """
        Generates a custom wordlist based on the gathered profile data,
        potentially using AI/ML techniques (conceptual).
        """
        if not self.generate_wordlist:
            self.logger.info("[OSINT] Wordlist generation not requested.")
            return None

        self.logger.info("[OSINT] Generating AI/ML-powered custom wordlist...")
        wordlist_content = []

        if profile_data.get("company_name"):
            company = profile_data["company_name"]
            wordlist_content.append(company.lower())
            wordlist_content.append(company.capitalize())
            wordlist_content.append(f"{company.lower()}1")
            wordlist_content.append(f"{company.capitalize()}123")
            wordlist_content.append(f"{company.lower()}2024")

        if profile_data.get("known_employees"):
            for email in profile_data["known_employees"]:
                username = email.split('@')[0]
                wordlist_content.append(username)
                wordlist_content.append(f"{username}123")

        # Example of adding common patterns
        wordlist_content.extend(["password", "123456", "admin", "qwerty"])
        
        # Simulate AI/ML by adding permutations based on current time/date
        current_year = str(time.localtime().tm_year)
        wordlist_content.append(f"Summer{current_year}!")
        wordlist_content.append(f"{current_year}!")

        # Deduplicate and sort
        unique_words = sorted(list(set(wordlist_content)))
        
        wordlist_filename = os.path.join(self.output_dir, f"custom_wordlist_{int(time.time())}.txt")
        try:
            with open(wordlist_filename, 'w', encoding='utf-8') as f:
                for word in unique_words:
                    f.write(word + '\n')
            self.logger.info(f"[OSINT] Custom wordlist generated: {wordlist_filename} with {len(unique_words)} entries.")
            self.findings.append({"type": "generated_wordlist", "path": wordlist_filename, "count": len(unique_words)})
            return wordlist_filename
        except IOError as e:
            self.logger.error(f"[OSINT] Failed to write custom wordlist: {e}")
            return None


    def execute_profiling(self) -> bool:
        """
        Executes the OSINT profiling and breach checking process.
        """
        self.logger.info("[OSINT] Starting OSINT Profiler execution...")
        profile_data: Dict[str, Any] = {}
        
        # Phase 1: Data Breach Checks (HIBP)
        if self.target_email or self.target_domain:
            breach_results = self._check_breaches_hibp(self.target_email, self.target_domain)
            if breach_results:
                self.findings.append({"type": "hibp_breaches", "results": breach_results})
                self.logger.info(f"[OSINT] Recorded {len(breach_results)} HIBP breach findings.")
            else:
                self.logger.info("[OSINT] No HIBP breaches found for specified email/domain.")
        else:
            self.logger.info("[OSINT] No email or domain provided for HIBP check. Skipping.")

        # Phase 2: General Target Profiling
        profile_data = self._profile_target_osint(self.profile_company_name, self.target_username)
        if profile_data:
            self.logger.info("[OSINT] Target profiling complete.")
        else:
            self.logger.info("[OSINT] No specific company or username provided for general profiling. Skipping.")

        # Phase 3: AI/ML Wordlist Generation
        if self.generate_wordlist:
            wordlist_path = self._generate_ai_ml_wordlist(profile_data)
            if wordlist_path and self.enrich_appstate:
                self.app_state.set_runtime_meta("osint_generated_wordlist", wordlist_path)
                self.logger.info(f"[OSINT] Stored generated wordlist path in AppState: {wordlist_path}")

        # Phase 4: Enrich AppState (if requested)
        if self.enrich_appstate:
            self.logger.info("[OSINT] Enriching AppState with OSINT findings...")
            self.app_state.set_runtime_meta("osint_profiler_findings", self.findings)
            # You might want to update specific AppState schemas like 'targets' or 'credentials'
            # For example:
            # if self.target_email and self.findings.get("hibp_breaches"):
            #     # Logic to add to AppState.get_discovery_graph().get("credentials") or new "leaks" section
            self.logger.info("[OSINT] AppState updated with OSINT findings summary.")

        # Save all findings to a local file
        try:
            with open(self.output_filepath, 'w', encoding='utf-8') as f:
                json.dump(self.findings, f, indent=4)
            self.logger.info(f"[OSINT] All OSINT findings saved to: {self.output_filepath}")
        except IOError as e:
            self.logger.error(f"[OSINT] Failed to save OSINT findings to file: {e}")
            return False

        self.logger.info("[OSINT] OSINT Profiler execution finished.")
        return True

    def cleanup(self):
        """No specific cleanup needed for this plugin after execution, findings are saved."""
        self.logger.debug("[OSINT] OSINT Profiler cleanup completed.")

# --- MAIN ENTRY POINT FOR PLUGIN ---
def run(app_context: CapGateContext, *plugin_args: str):
    """
    Plugin entry point for the OSINT Profiler.
    """
    profiler_succeeded: bool = False
    osint_profiler: Optional[OSINTProfiler] = None

    try:
        logger.info("[PLUGIN OSINT Profiler] Starting OSINT Profiler orchestration...")

        # Parse plugin_args into app_context before initializing the profiler
        # This ensures the profiler has access to the CLI arguments from its __init__
        for i, arg in enumerate(plugin_args):
            if arg == "--target-email" and i + 1 < len(plugin_args):
                app_context.set("target_email", plugin_args[i+1])
            elif arg == "--target-domain" and i + 1 < len(plugin_args):
                app_context.set("target_domain", plugin_args[i+1])
            elif arg == "--target-username" and i + 1 < len(plugin_args):
                app_context.set("target_username", plugin_args[i+1])
            elif arg == "--pwned-api-key" and i + 1 < len(plugin_args):
                app_context.set("pwned_api_key", plugin_args[i+1])
            elif arg == "--profile-company" and i + 1 < len(plugin_args):
                app_context.set("profile_company", plugin_args[i+1])
            elif arg == "--output-dir" and i + 1 < len(plugin_args):
                app_context.set("output_dir", plugin_args[i+1])
            elif arg == "--enrich-appstate":
                app_context.set("enrich_appstate", True)
            elif arg == "--generate-wordlist":
                app_context.set("generate_wordlist", True)
        
        osint_profiler = OSINTProfiler(app_context)
        
        profiler_succeeded = osint_profiler.execute_profiling()
        
        if profiler_succeeded:
            logger.info("[PLUGIN OSINT Profiler] Profiling completed successfully!")
        else:
            logger.warning("[PLUGIN OSINT Profiler] Profiling finished with issues.")

    except Exception as e:
        from base.debug_tools import print_exception
        print_exception(e, "[PLUGIN OSINT Profiler] An unexpected error occurred during execution")
        logger.error(f"[PLUGIN OSINT Profiler] Plugin failed due to an unexpected error: {e}")
        profiler_succeeded = False
    finally:
        if osint_profiler:
            osint_profiler.cleanup()

    return profiler_succeeded