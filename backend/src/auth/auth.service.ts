import { ConflictException, Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { JwtService } from '@nestjs/jwt';
import * as bcrypt from 'bcrypt';
import { UsersService } from '../users/users.service';
import { User } from '../users/entities/user.entity';
import { UserResponseDto } from '../users/dto/user-response.dto';
import { UserTransformer } from '../users/transformers/user.transformer';
import { RegisterDto } from './dto/register.dto';
import { AuthResponseDto } from './dto/auth-response.dto';

@Injectable()
export class AuthService {
  constructor(
    private usersService: UsersService,
    private jwtService: JwtService,
    private configService: ConfigService,
  ) {}

  async validateUser(email: string, password: string): Promise<User | null> {
    const user = await this.usersService.findByEmail(email);
    if (!user) return null;
    const valid = await bcrypt.compare(password, user.passwordHash);
    return valid ? user : null;
  }

  async register(dto: RegisterDto): Promise<UserResponseDto> {
    const existing = await this.usersService.findByEmail(dto.email);
    if (existing) throw new ConflictException('Email already registered');

    const passwordHash = await bcrypt.hash(dto.password, 10);
    const user = await this.usersService.createUser(dto.email, passwordHash, dto.firstName, dto.lastName);

    return UserTransformer.toResponse(user);
  }

  async login(user: User): Promise<AuthResponseDto> {
    const payload = { sub: user.id, email: user.email };
    const expiresIn = parseInt(this.configService.get<string>('JWT_EXPIRES_IN') ?? '86400', 10);

    return {
      accessToken: await this.jwtService.signAsync(payload),
      expiresIn: expiresIn,
    };
  }
}
