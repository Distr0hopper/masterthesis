import { User } from '../entities/user.entity';
import { UserResponseDto } from '../dto/user-response.dto';

export class UserTransformer {
    static toResponse(user: User): UserResponseDto {
        return {
            id: user.id,
            email: user.email,
            firstName: user.firstName,
            lastName: user.lastName,
            createdAt: user.createdAt,
        };
    }
}