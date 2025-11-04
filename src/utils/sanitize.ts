import DOMPurify from 'dompurify';

/**
 * XSS Protection Utility
 *
 * Provides sanitization functions to prevent XSS attacks in user-generated content.
 * Uses DOMPurify for robust HTML/script tag removal.
 */

/**
 * Sanitize user input to prevent XSS attacks
 * Strips all HTML tags and potentially malicious content
 *
 * @param input - User-provided string that may contain malicious content
 * @returns Sanitized string safe for rendering
 */
export function sanitizeText(input: string | null | undefined): string {
  if (!input) return '';

  // Configure DOMPurify to strip all HTML tags
  const cleanText = DOMPurify.sanitize(input, {
    ALLOWED_TAGS: [], // No HTML tags allowed
    ALLOWED_ATTR: [], // No attributes allowed
    KEEP_CONTENT: true, // Keep text content
  });

  return cleanText.trim();
}

/**
 * Sanitize HTML content allowing only safe tags
 * Use this when you need to preserve some formatting (e.g., bold, italic)
 *
 * @param html - HTML string that may contain user content
 * @returns Sanitized HTML safe for rendering via dangerouslySetInnerHTML
 */
export function sanitizeHTML(html: string | null | undefined): string {
  if (!html) return '';

  // Allow only safe formatting tags
  const cleanHTML = DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'br', 'p', 'span'],
    ALLOWED_ATTR: [],
    KEEP_CONTENT: true,
  });

  return cleanHTML;
}

/**
 * Sanitize and validate email addresses
 * Prevents XSS in email fields while allowing valid email formats
 *
 * @param email - Email address string
 * @returns Sanitized email or empty string if invalid
 */
export function sanitizeEmail(email: string | null | undefined): string {
  if (!email) return '';

  // Remove any HTML/script tags
  const cleaned = sanitizeText(email);

  // Basic email validation pattern
  const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

  return emailPattern.test(cleaned) ? cleaned : '';
}

/**
 * Sanitize URL to prevent javascript: and data: protocols
 *
 * @param url - URL string
 * @returns Sanitized URL or empty string if potentially malicious
 */
export function sanitizeURL(url: string | null | undefined): string {
  if (!url) return '';

  const cleaned = url.trim().toLowerCase();

  // Block dangerous protocols
  if (cleaned.startsWith('javascript:') ||
      cleaned.startsWith('data:') ||
      cleaned.startsWith('vbscript:')) {
    return '';
  }

  return url.trim();
}

/**
 * React component helper to safely render user content
 *
 * @param content - User-generated content
 * @returns Object for use with dangerouslySetInnerHTML (already sanitized)
 */
export function createSafeMarkup(content: string | null | undefined): { __html: string } {
  return {
    __html: sanitizeHTML(content)
  };
}
