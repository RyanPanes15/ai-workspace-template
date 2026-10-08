import React, { useState } from 'react';

export function CustomerForm() {
  const [name, setName] = useState('');
  return (
    <form>
      <input value={name} onChange={(e) => setName(e.target.value)} />
    </form>
  );
}
