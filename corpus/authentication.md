# Authentication And SSO

Password reset emails normally arrive within five minutes. Customers should check
spam folders and verify that their email address matches the account email. If a
reset email does not arrive after ten minutes, ask the customer to retry once and
then escalate with the account email and timestamp.

Single sign-on uses the customer's identity provider metadata. If SSO users cannot
sign in, confirm that the SAML metadata URL is reachable, the certificate has not
expired, and the user is assigned to the application in the identity provider.
Escalate persistent SSO failures to the identity team with the tenant ID and error
message.

