'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '@/store/useAuthStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuthStore();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirm) {
      setError('Пароли не совпадают');
      return;
    }
    if (password.length < 4) {
      setError('Пароль должен быть минимум 4 символа');
      return;
    }

    setLoading(true);
    try {
      await register(email, name, password);
      router.push('/dashboard');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Ошибка регистрации');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-[#f9f9f9] dark:bg-[#171717] px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-xl font-bold">Yuriy AI</h1>
          <p className="text-sm text-gray-500">Создайте аккаунт</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            placeholder="Имя"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <Input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Input
            type="password"
            placeholder="Пароль"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <Input
            type="password"
            placeholder="Подтвердите пароль"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
          />

          {error && (
            <p className="text-sm text-red-500 text-center">{error}</p>
          )}

          <Button type="submit" disabled={loading} className="w-full h-11 rounded-xl">
            {loading ? 'Регистрация...' : 'Зарегистрироваться'}
          </Button>
        </form>

        <p className="text-sm text-center text-gray-400">
          Уже есть аккаунт?{' '}
          <Link href="/login" className="text-black dark:text-white underline underline-offset-2">
            Войти
          </Link>
        </p>
      </div>
    </div>
  );
}
