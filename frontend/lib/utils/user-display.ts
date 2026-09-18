/** Derive a readable display name, preferring the user's full name and
 * falling back to a name guessed from the email local-part,
 * e.g. "marie.dupont+crm@acme.io" -> "Marie Dupont". */
export function getDisplayName(fullName: string | undefined | null, email: string | undefined | null): string {
  if (fullName && fullName.trim().length > 0) return fullName.trim();
  if (!email) return "Utilisateur";
  const localPart = email.split("@")[0]?.split("+")[0] ?? email;
  const words = localPart.split(/[.\-_]+/).filter(Boolean);
  if (words.length === 0) return email;
  return words.map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
}

export function getInitials(fullName: string | undefined | null, email: string | undefined | null): string {
  const name = getDisplayName(fullName, email);
  const words = name.split(" ").filter(Boolean);
  if (words.length >= 2) {
    return (words[0][0] + words[1][0]).toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}
