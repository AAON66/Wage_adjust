export interface PasswordStrength {
  score: number;
  label: string;
  toneStyle: { background: string; color: string };
  hint: string;
}

const LOWER = 'abcdefghijkmnopqrstuvwxyz';
const UPPER = 'ABCDEFGHJKLMNPQRSTUVWXYZ';
const NUMBERS = '23456789';
const SYMBOLS = '!@#$%^&*-_=+?';
const ALL = `${LOWER}${UPPER}${NUMBERS}${SYMBOLS}`;

function randomIndex(max: number): number {
  const buffer = new Uint32Array(1);
  window.crypto.getRandomValues(buffer);
  return buffer[0] % max;
}

function shuffle(values: string[]): string[] {
  const result = [...values];
  for (let index = result.length - 1; index > 0; index -= 1) {
    const swapIndex = randomIndex(index + 1);
    [result[index], result[swapIndex]] = [result[swapIndex], result[index]];
  }
  return result;
}

export function generateSecurePassword(length = 14): string {
  const targetLength = Math.max(length, 12);
  const seed = [
    LOWER[randomIndex(LOWER.length)],
    UPPER[randomIndex(UPPER.length)],
    NUMBERS[randomIndex(NUMBERS.length)],
    SYMBOLS[randomIndex(SYMBOLS.length)],
  ];

  while (seed.length < targetLength) {
    seed.push(ALL[randomIndex(ALL.length)]);
  }

  return shuffle(seed).join('');
}

export function assessPasswordStrength(password: string): PasswordStrength {
  let score = 0;

  if (password.length >= 8) score += 1;
  if (password.length >= 12) score += 1;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score += 1;
  if (/\d/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password)) score += 1;

  if (!password) {
    return {
      score: 0,
      label: '未设置',
      toneStyle: { background: 'var(--color-bg-subtle)', color: 'var(--color-placeholder)' },
      hint: '建议使用不少于 12 位，并混合大小写字母、数字和符号。',
    };
  }

  if (score <= 2) {
    return {
      score,
      label: '较弱',
      toneStyle: { background: 'var(--color-danger-bg)', color: 'var(--color-danger)' },
      hint: '建议补充大小写字母、数字和符号，并增加密码长度。',
    };
  }

  if (score <= 4) {
    return {
      score,
      label: '中等',
      toneStyle: { background: 'var(--color-warning-bg)', color: 'var(--color-warning)' },
      hint: '已具备基本强度，建议继续增加长度或符号组合。',
    };
  }

  return {
    score,
    label: '较强',
    toneStyle: { background: 'var(--color-success-bg)', color: 'var(--color-success)' },
    hint: '密码强度较好，适合作为内部平台账号密码。',
  };
}
